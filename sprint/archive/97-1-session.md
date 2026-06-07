---
story_id: "97-1"
jira_key: ""
epic: "97"
workflow: "tdd"
---
# Story 97-1: Pool-member relationship projection gap — engaged npc_pool members never get ADR-136 cards

## Story Details
- **ID:** 97-1
- **Title:** Pool-member relationship projection gap — engaged npc_pool members never get ADR-136 cards
- **Points:** 3
- **Priority:** p1
- **Type:** bug
- **Repos:** server
- **Workflow:** tdd
- **Stack Parent:** none

## Branch Information
- **Branch Strategy:** gitflow (story/97-1-pool-relationship-projection)
- **Repository:** sidequest-server
- **Base:** origin/develop

## Design Spec
- docs/superpowers/specs/2026-06-07-pool-relationship-projection-promotion-design.md

## Context
- sprint/context/context-story-97-1.md
- sprint/context/context-epic-97.md

## Acceptance Criteria
1. An engaged npc_pool member with relationship-relevant history appears on the Relationships tab
2. A latent/unseen pool member does not (seen-gate semantics preserved)
3. OTEL span on the promotion/projection decision (lie-detector)

**Phase:** finish
**Phase Started:** 2026-06-07T16:42:40Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-07T15:44:41Z | 2026-06-07T15:45:30Z | ~1m |
| red | 2026-06-07T15:45:30Z | | |

> **NOTE (TEA):** the testing-runner subagent clobbered this session file with its
> test report (known failure mode — memory `feedback_testing_runner_clobbers_session`);
> reconstructed by TEA from setup-time content. Test run results preserved below.

## Tea Assessment

**RED state:** VERIFIED (full suite, run_id `97-1-tea-red`, 211.9s)
**New tests:** `tests/server/test_pool_relationship_projection.py` — 21 tests: **13 failing** (feature absent), **8 passing** (negative gate-pins protecting current correct behavior from overshoot). Committed `7187a437` on `story/97-1-pool-relationship-projection`.

### Full-suite baseline (memory: gate on the FULL suite)
- **passed:** 11,174 · **failed:** 17 · **skipped:** 371
- 13 failures = the new RED tests (expected)
- 4 failures = known baseline, NOT regressions:
  - `test_earthman_boon_is_world_tier_not_engine_hardcode` (epic-96)
  - `test_opponent_roll_broadcasts_dice_pair` (epic-96)
  - `test_extracted_name_and_renamed_rig_land_on_snapshot` + `test_extraction_decisions_are_observable` — the 97-6 xdist flake pair, fired this run (fresh evidence for story 97-6)
- Neighbor suites green pre-commit: test_relationships_seen_gate, test_relationships_emit, test_npc_development_pipeline, test_npc_pool_narration_apply, test_update_npc_disposition (73 passed).

### Test strategy (per approved design spec)
All tests drive REAL production seams (no source-text wiring): `_apply_npc_mentions` (engagement), `build_relationship_entries` (projection), `_maybe_emit_relationships` (emit + change-gate), registered `update_npc_disposition` handler (valence trigger), `otel_capture` fixture (span assertions).

| AC | Tests |
|----|-------|
| AC 1 (engaged member cards) | cited_pool_member_projects, third_deduped_interaction_promotes, promotion_carries_state, promoted_member_yields_exactly_one_card, promoted_member_recite_reconciles, valence_beat_promotes, emit_includes_engaged_pool_member (wiring), change_gate_fires_on_new_pool_engagement |
| AC 2 (seen-gate preserved) | latent_pool_member_not_projected, dialogue_only_mint_not_projected (Captain Hale shape), unratified_pool_member_not_projected (ADR-138 is_projectable), hostile_cited_pool_member_not_projected, roster_npcs_still_project_unchanged |
| AC 3 (OTEL both branches) | projection_emits_pool_projected_span, projection_skip_emits_span_with_reason, tier_promotion_emits_span_with_trigger, valence_beat_promotes (trigger=valence_beat attr), valence_beat_on_live_opponent (npc.promotion_skipped reason=hostile_context) |
| Invariants | same_turn_and_same_call_cites_dedupe (97-5 double-apply shape), below_threshold_does_not_promote, hostile_member_never_promotes_mid_fight, resolved_encounter_releases_pool_gate |

### Rule Coverage (lang-review/python.md)
- **#6 test quality:** self-checked — every test asserts specific values/names; no vacuous assertions; negative cases paired with positives; failing-message on the not_found assertion names the expected status.
- **#3 type annotations:** all test helpers annotated.
- **#1/#4 (silent exceptions/logging):** enforced via AC-3 span tests — both decision branches MUST emit (the decline-silence class of bug).
- Remaining checks (#2,5,7-12) target implementation code — Dev's diff will be measured against them at spec-check/review.

### Notes for Dev (Major Winchester)
1. **The sharpest failing test:** `test_valence_beat_promotes_cited_pool_member` — `update_npc_disposition` (sidequest/agents/tools/update_npc_disposition.py:105) searches `snapshot.npcs` only → `not_found` for pool members.
2. **Engagement tracking does not exist on `NpcPoolMember`** — the pool_hit branch (narration_apply.py:2186-2239) upserts identity but tracks no presence/interaction. You'll need fields + the per-turn dedupe parallel to `Npc.last_development_turn` (the dedupe test pins the 97-5 double-apply shape).
3. **Hostile gate reuse:** `_engagement_is_hostile_context` (narration_apply.py:1893) does `npc.core.name` — pool members have `.name`, not `.core.name`; adapt, don't duplicate.
4. **Promotion path reuse:** `_promote_pool_member_to_npc` (narration_apply.py:1196) already carries `invented_from` + disposition; promotion must ALSO carry interaction count + beat log (the carries_state test pins it).
5. **ADR-138:** `is_projectable` (npc_pool.py:105) is the shared ratification gate — wire it, don't re-implement (unratified test pins it).
6. **Emit change-gate:** `_relationships_signature` (relationships_emit.py:26) reads `snapshot.npcs` only — the change_gate test pins pool incorporation.

## Design Deviations

### TEA (test design)
- **Promotion removes the pool entry (vs existing shadow convention)**
  - Spec source: docs/superpowers/specs/2026-06-07-pool-relationship-projection-promotion-design.md, "Leg 2 — Promotion"
  - Spec text: "After promotion the pool entry is removed. The relationship card re-sources from the roster under the same name key — exactly one card, one identity, before and after."
  - Implementation: `test_promotion_carries_state` asserts the pool entry is GONE post-promotion, per spec. NOTE: the existing mechanical-promotion convention (npc_pool.py docstring, narration_apply.py:1378 path) SHADOWS the member instead ("the pool member remains in GameSnapshot.npc_pool and is shadowed by the Npc lookup"). The spec is the higher authority (spec-authority hierarchy) so the test pins removal — but Dev/Architect should consciously decide whether the OTHER promotion path converges on removal too, or whether the two paths deliberately differ. Flagged for spec-check.
  - Type: Behavioral
  - Severity: Minor
  - Forward impact: if shadowing is ruled correct instead, one assertion in test_promotion_carries_state changes; the one-card invariant (the real AC) holds either way.
  - → ✓ ACCEPTED by Reviewer: spec is the higher authority and explicitly specifies removal; the legacy shadow path is untouched and the convergence question is properly filed as a delivery finding — divergence is documented, not silent.

### Dev (implementation)
- **Two stale test pins amended (superseded by the 97-1 design)**
  - Spec source: docs/superpowers/specs/2026-06-07-pool-relationship-projection-promotion-design.md, "Decisions" §2 + "Testing"
  - Spec text: "Promote when the ADR-128 ladder crosses acquaintance (3 deduped interactions...)" and "Regression: test_disposition_does_not_drift_without_a_stateful_npc"
  - Implementation: the spec listed that test as a stay-green regression, but its original form drove 5 cites and asserted NO Npc ever appears — directly contradicted by the designed promotion at 3. Amended to pin the SURVIVING invariant (sub-threshold cites mint nothing, pool disposition unmoved). Same shape for test_npc_pool_member_rejects_extra_fields, whose example "extra" field was literally last_seen_location — a field the design deliberately adds; probe now uses a genuinely unknown field, extra="forbid" discipline unchanged.
  - Rationale: the #742 precedent ("3 updated — the updated ones pinned the per-cite invariant this fix deliberately supersedes"); spec authority over older code pins.
  - Severity: minor
  - Forward impact: none — both tests still pin their load-bearing invariants; the promotion behavior is pinned in test_pool_relationship_projection.py.
  - → ✓ ACCEPTED by Reviewer: verified both amended tests against the diff — each still asserts its surviving invariant with specific values (sub-threshold no-mint + pool disposition unmoved; extra="forbid" via a genuinely-unknown probe field); matches the #742 precedent for deliberately-superseded pins.
- **Hostile-skip valence beat returns ToolResult.ok with a skipped payload (tool contract not specified)**
  - Spec source: docs/superpowers/specs/2026-06-07-pool-relationship-projection-promotion-design.md, "Invariants preserved" (hostile-context gate)
  - Spec text: "a pool member seated as a live opponent accrues no development ticks and cannot promote mid-fight"
  - Implementation: update_npc_disposition on a live-opponent pool member returns ok with {"skipped": "hostile_context", detail} plus the npc.promotion_skipped span — no state change. The spec did not define the tool's return contract for this branch.
  - Rationale: an error return would make the narrator retry/apologize mid-fight; an ok-with-reason gives it usable feedback. The span keeps the decline observable (never silent).
  - Severity: minor
  - Forward impact: if the narrator should instead queue the beat for post-encounter application, that's a follow-up design choice; nothing downstream assumes the current return shape.
  - → ✓ ACCEPTED by Reviewer: ok-with-skipped-payload + npc.promotion_skipped span is honest (not a silent fallback — the decline is visible on two channels) and an error return would provoke narrator retry loops mid-combat; contract gap was genuinely unspecified in the spec.

## Delivery Findings

### Dev (implementation)
- **Improvement** (non-blocking): the legacy mechanical-promotion path still SHADOWS the pool member while the new 97-1 path REMOVES it — two promotion conventions now coexist. Affects `sidequest/server/narration_apply.py` (the :1378-area mechanical promotion call site should converge on removal or the difference should be documented). *Found by Dev during implementation.*
- **Gap** (non-blocking): full-suite parallel runs crash xdist workers on heavy e2e wiring tests with drifting membership (pertinence/retrieval/lore_rag/culture_context/chargen_no_hp_leak this session) — process-level "worker gwN crashed", no traceback; all pass serially and in small groups. Same isolation family as story 97-6; that story's fix should account for worker memory pressure, not just span-exporter state. Affects `tests/` xdist configuration. *Found by Dev during implementation.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/npc_pool.py` — NpcPoolMember gains engagement state: last_seen_turn/location, non_transactional_interactions, last_development_turn (97-5-shape per-turn dedupe)
- `sidequest/server/narration_apply.py` — pool_hit branch: presence stamp + deduped interest tick + #742 hostile gate (generalized for both entity shapes) + tier-trigger promotion; new `_promote_engaged_pool_member` (wraps the existing `_promote_pool_member_to_npc`, carries engagement state, removes pool entry, emits npc.promoted_from_pool)
- `sidequest/game/projection/relationships.py` — pool source in build_relationship_entries behind the seen-gate predicate; npc.pool_projected / npc.pool_projection_skipped spans on both branches
- `sidequest/server/websocket_handlers/relationships_emit.py` — change-gate signature incorporates pool engagement; empty-guard considers pool
- `sidequest/agents/tools/update_npc_disposition.py` — valence trigger: pool fallback lookup → hostile gate (npc.promotion_skipped) or promotion (trigger=valence_beat), then the existing beat-recording flow on the promoted Npc (function-local server import per the long_rest.py precedent)
- `tests/server/test_npc_development_pipeline.py`, `tests/game/test_npc_pool_model.py` — stale pins amended (see deviations)

**Tests:** 21/21 story tests passing (GREEN); affected suites 105 passed; lint + format clean.
**Full suite:** GREEN at baseline — 11,187 passed / 371 skipped; failures = 2 known epic-96 baseline (earthman boon, reprisal broadcast-pair) + the drifting xdist worker-crash flake family (97-6 territory; measured across 2 full runs + 4 group runs: membership drifts, all members pass serially — process crashes, not assertion failures).
**Branch:** story/97-1-pool-relationship-projection (pushed, 359e2582; RED tests 7187a437)

**Handoff:** Spec-check (Major Houlihan), then verify/review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (100/100 tests GREEN, lint+format clean, 0 smells, noqa/type-ignore annotations all justified) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — domain covered by Reviewer directly (see observations 1, 6) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — domain covered by Reviewer directly (see observation 5) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — domain covered by Reviewer directly (see observation 8 + deviation audit of amended pins) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — docstrings on all new fields/functions verified accurate against behavior |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — domain covered by Reviewer directly (see observation 2) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings — no user-input parsing, no SQL/eval/subprocess in diff; npc_id is an exact-match name lookup; tenant isolation N/A (single-operator personal project) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — domain covered by Reviewer directly (see observation 3); no dead code, helper reuses existing promotion path per Don't-Reinvent |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — Rule Compliance section below is the manual exhaustive pass |

**All received:** Yes (1 returned clean, 8 disabled via settings)
**Total findings:** 3 confirmed (1 Medium, 2 Low), 0 dismissed, 0 deferred

### Rule Compliance (lang-review/python.md, manual exhaustive pass over the diff)

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | Silent exception swallowing | PASS | zero try/except added anywhere in the diff |
| 2 | Mutable default arguments | PASS | all new pydantic fields are scalars (int/str\|None); no def with mutable defaults |
| 3 | Type annotations at boundaries | PASS | `_promote_engaged_pool_member` fully annotated (kw-only, -> Npc); `_pool_projection_skip_reason(member: NpcPoolMember) -> str \| None`; trigger is bare `str` — see observation 2 (Low, Literal would be tighter) |
| 4 | Logging coverage AND correctness | PASS | promotion INFO (narration_apply.py:1322), pool skip INFO (:2341); lazy %-style throughout; no sensitive data |
| 5 | Path handling | N/A | no path operations in diff |
| 6 | Test quality | PASS | preflight annotations verified; amended pins assert specific values; no vacuous assertions introduced |
| 7 | Resource leaks | N/A | no resources acquired |
| 8 | Unsafe deserialization | N/A | none |
| 9 | Async/await pitfalls | PASS | tool handler remains async with no blocking calls added; promotion helper is sync called from sync context |
| 10 | Import hygiene | PASS | function-local server import in the tool is deliberate anti-cycle (long_rest.py:103 precedent, comment cites it); no star imports |
| 11 | Input validation at boundaries | PASS | tool args validated by existing pydantic UpdateNpcDispositionArgs; npc_id exact-match only |
| 12 | Dependency hygiene | N/A | no dependency changes |
| 13 | Fix-introduced regressions | PASS | re-scanned the two test amendments against #1-#12 — clean |

Project-rule sweep (CLAUDE.md/SOUL.md): **No Silent Fallbacks** — every decline branch emits span+log (verified at relationships.py skip span, tool skip span+payload, narration skip span; the two `getattr(snapshot, "npc_pool", [])` defaults are the documented duck-typed-test robustness precedent, not real-state fallbacks). **OTEL Observability** — all four decision spans present, both branches. **Don't Reinvent** — promotion wraps `_promote_pool_member_to_npc`; ratification reuses `is_projectable`; hostile gate generalized not duplicated. **Wiring** — integration tests drive the real emitter; production reachability verified below.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** narrator mention "Rifenna Muse" → `_apply_npc_mentions` Step-2 pool_hit (narration_apply.py:2316 presence stamp → :2327 dedupe guard → :2329 hostile gate → :2349 tick) → 3rd deduped tick crosses ACQUAINTANCE_AT → `_promote_engaged_pool_member` (:2356) → snapshot.npcs append + pool remove (:1306-1307) → `build_relationship_entries` roster walk picks it up → `_maybe_emit_relationships` signature moves (pool part, relationships_emit.py:49) → RELATIONSHIPS broadcast → UI tab. Safe because every hop is driven by the integration tests through the production emitter, and the seen-gate excludes unratified/unseen/uninteracted members before any entry is built.

**Observations (severity-tagged):**
1. **[MEDIUM] [EDGE] `last_development_turn` not carried across promotion** — `_promote_engaged_pool_member` (narration_apply.py:1293-1297) carries interactions/tier/last-seen but not the dedupe stamp; the freshly-promoted Npc has `last_development_turn=0`, so under the 97-5 double-apply shape a SECOND apply call in the promotion turn re-mentions the name, hits npcs_hit, passes `npc.last_development_turn != turn_num`, and ticks a 4th interaction in the same turn — the one-tick-per-turn contract leaks exactly once at the promotion boundary. Requires the upstream 97-5 bug to manifest; impact is +1 interaction count (no tier jump possible: 4 < 8). Non-blocking; one-line fix (`npc.last_development_turn = turn_num`) filed as a delivery finding to ride 97-5 or a follow-up.
2. **[LOW] [TYPE] `trigger: str` on `_promote_engaged_pool_member`** — a typo'd trigger silently skips the milestone-drift leg and stamps a wrong span attr; `Literal["tier", "valence_beat"]` would make the contract compiler-visible. Two call sites today, both literals.
3. **[LOW] [SIMPLE] skip-span volume** — a world with a large latent pregen pool emits one `npc.pool_projection_skipped` span per latent member per projection pass; harmless at current pool sizes (≤15) but worth a single aggregate span if pools grow.
4. **[VERIFIED] hostile gate generalization** — narration_apply.py:1986-1989: `core = getattr(npc, "core", None)` then name from core or `.name`; mention=None safe because :1979 uses `getattr(mention, "side", "")`. Complies with the adapt-don't-duplicate guidance and keeps one gate for both tiers.
5. **[VERIFIED] No Silent Fallbacks on every decline** — projection skip span (relationships.py:117-122), tool hostile-skip span + ok-with-reason payload (update_npc_disposition.py), narration hostile-skip span+INFO (:2330-2347). Complies with CLAUDE.md No-Silent-Fallbacks + the OTEL principle; AC 3 satisfied on both branches.
6. **[VERIFIED] `snapshot.npc_pool.remove(member)` is safe** — narration_apply.py:1307; pydantic value-equality means a hypothetical byte-identical duplicate removes an equal value (net state identical); non-identical members can't false-match. The mentions loop iterates `mentions`, not the pool — no mutation-during-iteration.
7. **[VERIFIED] one-card invariant across the promotion boundary** — promotion removes the pool entry (:1307) and the projection's two sources are therefore disjoint; pinned by test_promoted_member_yields_exactly_one_card.
8. **[VERIFIED] pre-promotion dedupe contract** — pool tick guarded by BOTH `developed_this_turn` and `last_development_turn` (narration_apply.py:2327), pinned by test_same_turn_and_same_call_cites_dedupe (the 97-5 shape).

**Pattern observed:** the promotion helper correctly WRAPS the existing `_promote_pool_member_to_npc` rather than reimplementing it (narration_apply.py:1292) — the Don't-Reinvent pattern done right; `invented_from`/disposition carry came free.

**Error handling:** unknown npc_id → not_found unchanged; pool member found but hostile → visible structured decline; no new exception paths introduced (zero try/except in diff).

### Devil's Advocate

Suppose this code is broken. The sharpest attack: **the narrator names a pool member every single turn** — a chatty barkeep cited turns 1-2-3 promotes to a full Npc with HP 10/10. Did the table want the barkeep mechanically seatable? Yes by design — that's literally ADR-014 coal→diamond and the operator-approved spec; the alternative (Rifenna invisible) is the measured bug. Second attack: **promotion mid-encounter** — a NEUTRAL pool member cited 3 times during someone else's fight promotes while an encounter is live; the hostile gate only blocks opponent-seated members. Could the new Npc disturb the encounter? No — promotion appends to snapshot.npcs and touches no encounter state; seating is a separate seam. Third: **save-compat** — old saves deserialize pool members without the four new fields; pydantic defaults (0/None) mean they read as never-seen, so projection correctly shows nothing until fresh engagement; no migration needed, verified by defaults. Fourth: **the valence tool on a roster name that ALSO exists in the pool** (shadowed identity) — the npcs lookup wins first, pool leg never runs; consistent with the shadow convention. Fifth: **what if `party_location` returns None** — presence stamp skips location but still stamps the turn; entry carries last_seen_location=None which the protocol model allows. Sixth: **MP** — disposition is global per ADR-136 (no per-recipient fork), so pool cards broadcast identically to all seats; the change-gate is handler-scoped (`_SIG_ATTR` per handler), and each handler's first post-change emit fires — same semantics the roster path already had. The one genuine crack the attack surfaced is observation 1 (dedupe stamp across promotion), already filed at Medium. I could not break anything else that the tests don't already pin.

**Handoff:** To Hawkeye (SM) for finish — PR creation + merge.

### Reviewer (code review)
- **Improvement** (non-blocking): carry the per-turn dedupe stamp across promotion — `_promote_engaged_pool_member` should set `npc.last_development_turn = turn_num` so the one-tick-per-turn contract holds across the boundary under the 97-5 double-apply shape. Affects `sidequest/server/narration_apply.py` (one line in the promotion helper). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): tighten `trigger` to `Literal["tier", "valence_beat"]`. Affects `sidequest/server/narration_apply.py` (signature only). *Found by Reviewer during code review.*