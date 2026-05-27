---
story_id: "59-17"
jira_key: null
epic: "59"
workflow: "tdd"
---
# Story 59-17: Dogfight confrontation fails to instantiate via production path

## Story Details
- **ID:** 59-17
- **Epic:** 59 — Intent Router — Mechanical-Engagement Spine
- **Jira Key:** N/A (SideQuest uses sprint YAML, not Jira)
- **Workflow:** tdd
- **Points:** 3
- **Type:** bug
- **Priority:** P1
- **Stack Parent:** none
- **Repos:** server

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-27T17:50:03Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-27T12:00:00Z | 2026-05-27T15:23:42Z | 3h 23m |
| red | 2026-05-27T15:23:42Z | 2026-05-27T15:33:01Z | 9m 19s |
| green | 2026-05-27T15:33:01Z | 2026-05-27T16:28:48Z | 55m 47s |
| spec-check | 2026-05-27T16:28:48Z | 2026-05-27T16:30:32Z | 1m 44s |
| verify | 2026-05-27T16:30:32Z | 2026-05-27T17:21:10Z | 50m 38s |
| review | 2026-05-27T17:21:10Z | 2026-05-27T17:29:30Z | 8m 20s |
| green | 2026-05-27T17:29:30Z | 2026-05-27T17:37:19Z | 7m 49s |
| spec-check | 2026-05-27T17:37:19Z | 2026-05-27T17:38:19Z | 1m |
| verify | 2026-05-27T17:38:19Z | 2026-05-27T17:42:57Z | 4m 38s |
| review | 2026-05-27T17:42:57Z | 2026-05-27T17:48:47Z | 5m 50s |
| spec-reconcile | 2026-05-27T17:48:47Z | 2026-05-27T17:50:03Z | 1m 16s |
| finish | 2026-05-27T17:50:03Z | - | - |

## Confirmed Repro (Verified by SM 2026-05-27)

**Test:** `tests/integration/test_dogfight_playtest_smoke.py::test_three_turn_dogfight_resolves_through_production_path`

**Failure Signature:** `AssertionError: instantiation failed to set snap.encounter`

**Location:** `tests/fixtures/dogfight_playtest_encounter.py:143`

**What fails:** The space_opera dogfight encounter is never set on `snap.encounter` when instantiation is driven through the production path `_apply_narration_result_to_snapshot` (in `make_dogfight_playtest_state`).

**Failure point:** The test dies at the instantiation assert BEFORE reaching the resolution assertions (those belong to sibling story 59-19).

## Acceptance Criteria

**AC1: Smoke test passes through full production path**
- Fixture: space_opera dogfight (3-turn playtest encounter)
- Instantiation path: `_apply_narration_result_to_snapshot` (production path, not test-only)
- **MUST:** `snap.encounter` is set (not None) immediately after instantiation
- **MUST:** The encounter object carries:
  - Both opposing sides seated (player + NPC opponent in the dogfight)
  - Dial state initialized to Setup phase
  - Beat selections available per the confrontation_def
- Verification: `test_three_turn_dogfight_resolves_through_production_path` passes; assert on `snap.encounter` succeeds

**AC2: Full resolution path verified (wiring test, CLAUDE.md)**
- Fixture: dogfight instantiated via production path (AC1)
- Proceed through 3 full turns (instantiation → turn 1 dispatch → narration → turn 2 dispatch → narration → turn 3 dispatch → narration → end)
- **MUST:** Each turn's dispatch_dice_throw or resolution subsystem fires (space_opera uses opposed_check, not simple DC)
- **MUST:** OTEL spans prove ordering: encounter.created → turn 1 dispatch → turn 1 narration → turn 2 dispatch → ... → encounter.resolved
- Verification: dogfight test suite reaches the `test_three_turn_dogfight_resolves_through_production_path` assertions that currently do not run

**AC3: Opponent seating is verified at instantiation time**
- Per ADR-116 ("a confrontation requires an Other"), the instantiation guard ensures both the player's side and the opponent's side have at least one actor seated
- If the opponent is not seated at instantiation, the confrontation MUST fail loud with explicit error (not silent no-op)
- Span: `encounter.instantiation_failed` or `encounter.opponent_missing` on failure
- Regression: a dogfight fixture with a missing opponent surfaces an ERROR span (not a silent None encounter)

**AC4: Cross-check ADR-116 and story 59-13 implementation**
- Verify that the ADR-116 "confrontation requires an Other" membership invariant is wired into the dogfight instantiation path
- Confirm 59-13's opponent-seating fix is live in the production instantiation codepath (not just in test fixtures)
- Tracing: instantiation → check both sides have actors → seat opponent if not already seated → commit encounter to snapshot

## Problem Statement

The dogfight subsystem (per ADR-077) integrates with the space_opera genre pack as a StructuredEncounter specialized for aerial combat. Instantiation via the production path `_apply_narration_result_to_snapshot` fails to seat the NPC opponent or set the encounter on the snapshot. The test halts at the instantiation assert, unable to proceed to the 3-turn resolution assertions.

### Suspected Root Cause (Hypothesis for Dev to Verify — NOT Confirmed)

**Unverified hypothesis only — test this, do not assume:**

Per ADR-116 ("a confrontation requires an Other") and story 59-13 (opponent seating), the opponent/Other may not be seated at instantiation time via the production path. The confrontation may never commit if the membership invariant is not satisfied. This is a hypothesis — the actual cause may differ.

Do NOT assume this hypothesis is correct; it is a starting point for investigation.

## Story Context

**Related Stories:**
- Story 59-19: Dogfight smoke fails to resolve through production path (resolution phase; blocked by this story's instantiation fix)
- Story 59-13: Chase confrontation write-back — apply beat metric delta, transition Setup→active, seat opponent (INERT-chase dual-dial frozen 0/7) [DONE 2026-05-26]
- Story 59-16: Confrontation beats — collapse to one filtered delivery path (kill emitter firewall bypass) [backlog]

**Related ADRs:**
- ADR-116: A Confrontation Requires an Other — Participant Membership Invariant, Single Opponent-Seater, End-on-No-Other [partial]
- ADR-077: Dogfight Subsystem via StructuredEncounter Extension
- ADR-113: Intent Router — Mechanical-Engagement Spine [partial]

**Key Files:**
- `tests/fixtures/dogfight_playtest_encounter.py` — dogfight fixture and `make_dogfight_playtest_state`
- `tests/integration/test_dogfight_playtest_smoke.py` — the wiring/repro test
- `sidequest/server/dispatch/encounter_lifecycle.py` — `instantiate_encounter_from_trigger`, location fallback, sealed-letter arity validator
- `sidequest/agents/subsystems/confrontation.py` — confrontation dispatch handler (`run_confrontation_dispatch`)
- `sidequest/server/intent_router_pass.py` — router pre-narrator pass (dispatches with `npcs_present=[]`)

> **NOTE (2026-05-27):** This session file was reconstructed by TEA after the `testing-runner` subagent clobbered it during the verify quality-pass gate (known failure mode — passing `STORY_ID` to testing-runner cache-writes `.session/{id}-session.md`). Content reassembled from conversation context; phase history and assessments are faithful to the originals.

## SM Assessment

**Setup complete — routing to DEV (red phase).**

Story 59-17 is a P1 bug blocking the dogfight (space_opera) smoke test. The instantiation path fails to seat the opponent and set the encounter on the snapshot. The confirmed repro is in place; acceptance criteria are stated; the suspected root cause (ADR-116 membership invariant) is provided as a hypothesis for Dev to verify, not as a conclusion.

- **Repos:** server only. Branch off develop (github-flow subrepo).
- **Workflow:** tdd → next agent **dev**, next phase **red**.
- **Coordination flag for Dev:** The hypothesis mentions story 59-13 (opponent seating, DONE 2026-05-26). Verify that 59-13's fix is wired into the PRODUCTION instantiation path, not just test fixtures.
- **No-fallbacks discipline:** If instantiation fails to seat the opponent, the error MUST surface (loud ERROR span), not be papered over with a silent null or default encounter.

## TEA Assessment

**Tests Required:** Yes
**Phase:** finish — failing tests written, RED confirmed.

**Diagnosis (MEASURED, not asserted — every claim below was probed live against the real space_opera pack):**

1. **The smoke-test fixture is stale.** `make_dogfight_playtest_state` drives instantiation through `_apply_narration_result_to_snapshot` with `result.confrontation=dogfight`. That instantiation block was **deliberately removed in Story 59-4 / ADR-113** (`narration_apply.py:2526`). Confrontation engagement is now **router-driven**. The original repro's failure signature is real but its attributed path is dead.

2. **The real production path is `intent_router_pass → run_dispatch_bank → run_confrontation_dispatch → instantiate_encounter_from_trigger`.** Probed `instantiate_encounter_from_trigger` directly: with an explicit opponent it correctly seats `red`+`blue` and sets `snap.encounter`. The helper is NOT broken.

3. **The genuine bug is an opponent-sourcing gap on the live router seam.** `execute_intent_router_pre_narrator_pass` invokes the dispatch bank with a **hardcoded `npcs_present=[]`** (`intent_router_pass.py:167`). For a dogfight (`sealed_letter_lookup`), `instantiate_encounter_from_trigger` **skips the location fallback** (`encounter_lifecycle.py:474` — fallback was non-sealed-letter only), so the scene opponent is never seated → sealed-letter arity validator sees 0 opponents → `SealedLetterArityError` → caught → **no encounter**. Reproduced twice (no opponent; hostile opponent present) — both return `{'error': 'sealed_letter_arity_rejected'}`, `snap.encounter` stays None. ADR-116 family, mechanism precise.

**Test Files:**
- `tests/server/dispatch/test_dogfight_instantiation_production_path.py` (new) — drives the real router engager `run_confrontation_dispatch` with the production-reality `npcs_present=[]`.

**Tests Written:** 3 (covering refined AC1/AC3)
| Test | Intent | State (RED) |
|------|--------|-------|
| `test_dogfight_instantiates_via_router_dispatch_with_scene_opponent` | RED — seat scene opponent (red/blue) with `npcs_present=[]` + one hostile NPC present | **failing** (`sealed_letter_arity_rejected`) |
| `test_dogfight_dispatch_without_any_opponent_refuses_one_sided` | GUARD — zero opponents → refuse (ADR-116) | passing (must stay) |
| `test_dogfight_instantiates_when_opponent_passed_explicitly` | REGRESSION — explicit `npcs_present` keeps working | passing (must stay) |

**Status:** RED confirmed (1 failing, 2 guards green).
**Handoff:** To Dev (Inigo Montoya) for GREEN.

**For Dev — GREEN requires a 2-part fix:**
1. **Production fix:** give the sealed-letter instantiation path a way to seat its single opponent from the scene when the router supplies `npcs_present=[]`. The location fallback is skipped for sealed-letter *on purpose* (bystander leak) — a real design choice. Arity-checked (1 ⇒ seat; 0 or >1 ⇒ loud rejection). **May warrant an Architect consult.** Do NOT paper over with a silent default opponent.
2. **Rewire the stale fixture:** `make_dogfight_playtest_state` must instantiate through the real production path (`run_confrontation_dispatch` / `instantiate_encounter_from_trigger`), not the removed `_apply_narration_result_to_snapshot` block.

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (blocking): Sealed-letter (dogfight) confrontations cannot instantiate via the live router path — the opponent is never sourced from the scene. Affects `sidequest/server/dispatch/encounter_lifecycle.py` (`instantiate_encounter_from_trigger` skips the location fallback for `sealed_letter_lookup`) in concert with `sidequest/server/intent_router_pass.py:167` (`npcs_present=[]`). *Found by TEA during test design.*
- **Conflict** (non-blocking): The story's confirmed-repro attributes the failure to `_apply_narration_result_to_snapshot`, but that instantiation block was removed in Story 59-4 / ADR-113. The smoke-test fixture drives that dead path and must be rewired. Affects `tests/fixtures/dogfight_playtest_encounter.py` and `tests/integration/test_dogfight_playtest_smoke.py`. *Found by TEA during test design.*
- **Question** (non-blocking): The sealed-letter location-fallback skip was deliberate (bystander-leak avoidance). Seating one scene opponent for a duel may need an Architect ruling on which scene NPC qualifies as "the" opponent when several are present. Affects `sidequest/server/dispatch/encounter_lifecycle.py`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): Sealed-letter (dogfight) instantiation with >1 NPC at the player's location conservatively trips `SealedLetterArityError` and refuses to engage, even when only one is a genuine adversary (e.g. enemy pilot + friendly wingman). Safe and loud today, but a smarter single-adversary selector would let the duel start. A reliable hostility signal for narrator-declared NPCs (which default to NEUTRAL disposition) is the missing piece — disposition alone is insufficient. Affects `sidequest/server/dispatch/encounter_lifecycle.py` (`_npc_fallback_at_location` / sealed-letter seating). *Found by Dev during implementation.*

### TEA (test verification)
- No additional upstream findings during test verification. Simplify fan-out (reuse/quality/efficiency) surfaced only out-of-scope micro-DRY (declined); engine change is clean.

### Dev (implementation — rework R1)
- **Gap** (non-blocking): For the live router dogfight path to engage, the scene's opponent NPC must carry a hostile signal — either `disposition.attitude()==HOSTILE` (bestiary creatures default -20) or an adversarial `npc_role_id` (`_ADVERSARIAL_ROLE_IDS`). A narrator-declared opponent with `npc_role_id=None` and neutral disposition will (correctly, per 45-33) NOT be seated from the location fallback, so the dogfight refuses loudly. The narrator/materializer should tag dogfight opponents hostile. Affects narrator NPC-declaration / `world_materialization` tagging and `sidequest/server/dispatch/encounter_lifecycle.py:_npc_is_adversary`. *Found by Dev during rework.*

### Reviewer (code review)
- **Conflict** (blocking): The 59-17 guard relaxation regresses the Story 45-33 invariant — a lone bystander at the player's location is silently seated into a sealed-letter duel. `tests/server/test_encounter_lifecycle.py::test_sealed_letter_empty_npcs_present_raises_without_consuming_fallback` is RED on this branch (confirmed live: "DID NOT RAISE ValueError"). Affects `sidequest/server/dispatch/encounter_lifecycle.py:494` (the sealed-letter fallback needs an adversarial-role candidate filter keyed on `npc_role_id`, not disposition/category). *Found by Reviewer during code review.*
- **Gap** (non-blocking): No dispatch-level test covers the lone-bystander sealed-letter shape; the new `test_dogfight_instantiation_production_path.py` only exercises hostile-opponent and zero-opponent cases, so green looked clean while 45-33 (a module-level test outside the story's test dir) was red. TEA should add a bystander-only sealed-letter case to the new file so the gap can't reopen. Affects `tests/server/dispatch/test_dogfight_instantiation_production_path.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Whatever the green/verify test scope, a guard relaxation should be regression-run against the full owning module's tests, not just the story's new directory — the narrow `tests/server/dispatch/ + tests/integration/` scope is what let the regression reach review. *Found by Reviewer during code review.*

### Reviewer (code review — re-review R1)
- **Improvement** (non-blocking): `tests/server/dispatch/test_dogfight_instantiation_production_path.py` loads `space_opera_pack` module-scoped, which mutates the process-wide `_active_thresholds` global (`disposition.configure_attitude_thresholds`) with no `reset_attitude_thresholds()` teardown. Worker-isolated under the default `-n auto`; under serial `-n0` a later module could see space_opera's attitude band. `_npc_is_adversary`'s HOSTILE branch reads this global, so add a reset fixture for hygiene. Pre-existing fixture pattern (same in `test_sealed_letter_dispatch_integration.py`), not introduced by this story. Affects the test module's fixtures. *Found by Reviewer (security subagent) during re-review.*

## Impact Summary

**Upstream Effects:** 2 findings (0 Gap, 1 Conflict, 0 Question, 1 Improvement)
**Blocking:** 1 BLOCKING items — see below

**BLOCKING:**
- **Conflict:** The 59-17 guard relaxation regresses the Story 45-33 invariant — a lone bystander at the player's location is silently seated into a sealed-letter duel. `tests/server/test_encounter_lifecycle.py::test_sealed_letter_empty_npcs_present_raises_without_consuming_fallback` is RED on this branch (confirmed live: "DID NOT RAISE ValueError"). Affects `sidequest/server/dispatch/encounter_lifecycle.py:494`.

- **Improvement:** Sealed-letter (dogfight) instantiation with >1 NPC at the player's location conservatively trips `SealedLetterArityError` and refuses to engage, even when only one is a genuine adversary (e.g. enemy pilot + friendly wingman). Safe and loud today, but a smarter single-adversary selector would let the duel start. A reliable hostility signal for narrator-declared NPCs (which default to NEUTRAL disposition) is the missing piece — disposition alone is insufficient. Affects `sidequest/server/dispatch/encounter_lifecycle.py`.

### Downstream Effects

- **`sidequest/server/dispatch`** — 2 findings

### Deviation Justifications

6 deviations

- **Targeted the router seam, not `_apply_narration_result_to_snapshot`**
  - Rationale: The `_apply_narration_result_to_snapshot` instantiation block was removed in Story 59-4 / ADR-113 (confirmed at `narration_apply.py:2526`). The real production instantiation path is now the router → `run_confrontation_dispatch`. Asserting against the removed path would pin behavior to dead code. The observable AC is preserved — only the entrypoint under test changed to the live one.
  - Severity: minor
  - Forward impact: Dev must ALSO rewire the stale smoke-test fixture for the original repro to go green; see Delivery Findings.
- **Did not write the `encounter.instantiation_failed` / `encounter.opponent_missing` span assertion named in AC3**
  - Rationale: Pinning a test to a span name that doesn't exist would couple the test to a guessed implementation. The error-payload + no-encounter assertion is refactor-stable and proves the no-silent-fallback contract.
  - Severity: minor
  - Forward impact: none — guard test already enforces "loud refusal, not silent no-op".
- **Rejected the Architect consult's disposition-gating; seated via the existing category-keyed location fallback + arity validator**
  - Rationale: Verified against TEA's RED fixture and production reality — the consult's `disposition.attitude() == HOSTILE` gate is wrong here. TEA's RED opponent (`_seat_opponent`) carries the DEFAULT disposition (0 ⇒ NEUTRAL); a HOSTILE gate would exclude it and the RED test would fail. Not a test defect: only bestiary-materialized creatures default to hostile disposition (`session.py:1533` `disposition=-20 if is_creature`); a narrator-declared dogfight opponent — the live coyote_star case — is NEUTRAL too. Hostility in a dogfight is contextual to the scene, not a stored score, so the `_is_adversarial` CATEGORY check + arity is the correct discriminator. Reuse-first: no new code path, one condition relaxed. The consult's own goal (no silent bystander leak, no phantom opponent) is still met by the loud arity refusal.
  - Severity: minor
  - Forward impact: The >1-candidates-at-location case conservatively trips the arity refusal and the dogfight does not instantiate — safe and loud, but a smarter single-adversary selection is deferred to a future story. Recorded as a Delivery Finding. No sibling-story AC depends on multi-candidate seating.
- **Rewired the fixture via `instantiate_encounter_from_trigger` (sync primitive), not `run_confrontation_dispatch` (async)**
  - Rationale: TEA named both as acceptable. `instantiate_encounter_from_trigger` is the exact sync primitive `run_confrontation_dispatch` delegates to — same instantiation, role tagging, and OTEL — minus the dispatch's try/except that swallows engagement errors. For a fixture that WANTS instantiation to succeed and assert loudly on failure (no-silent-fallbacks), the primitive is correct: it raises instead of returning a swallowed error, and keeps the helper synchronous (the smoke test is sync). The router-with-empty-`npcs_present` path is covered by `test_dogfight_instantiation_production_path.py`.
  - Severity: trivial
  - Forward impact: none — sibling 59-19 consumes `snap.encounter`/`drive_dogfight_turn`, both unchanged.
- **Replaced the bare guard relaxation with an adversary-filtered sealed-letter fallback**
  - Rationale: This supersedes my flagged R0 reasoning. The Reviewer was right — arity catches 0/>1 but not the count==1 bystander, so an adversarial candidate filter IS required. The discriminator combines disposition (real signal for materialized creatures, default -20) with an `npc_role_id` adversarial allowlist (the signal both 45-33 "bystander" and 59-17 "hostile" tests carry), since narrator-declared opponents can be neutral-disposition. When hostility is ambiguous (None role + neutral) the predicate refuses (loud), never seats (No Silent Fallbacks).
  - Severity: major (fixes a regression of a shipped invariant)
  - Forward impact: A real narrator-declared dogfight opponent that is neither hostile-disposition nor adversarial-roled (e.g. `npc_role_id=None`) will NOT be seated from the fallback and the dogfight will refuse loudly. That is the safe direction, but it means the narrator/materializer should tag dogfight opponents with a hostile role or disposition for the live router path to engage. Logged as a Delivery Finding (Dev R1).
- **AC2 describes the resolution mechanism as `opposed_check`, but a dogfight resolves via `sealed_letter_lookup`**
  - Rationale: AC2's "opposed_check" wording is a spec inaccuracy — it conflates the generic combat resolution path with the dogfight's sealed-letter (commit-reveal) model. The observable intent of AC2 (three turns resolve end-to-end through the production dispatch path, with per-turn mechanical OTEL spans) is fully met by the now-green `test_three_turn_dogfight_resolves_through_production_path`. No code change is warranted; the spec text should be corrected to name the sealed-letter mechanism. (Note: full 3-turn *resolution* depth is sibling Story 59-19's charter; 59-17's charter is instantiation, which is satisfied.)
  - Severity: trivial (spec-text accuracy; no behavioral or code impact)
  - Forward impact: none on 59-17. Sibling 59-19 (dogfight resolution) should treat the dogfight as sealed-letter, not opposed_check, when authoring its resolution assertions.

## Architect Consult (green-phase, requested by TEA)

**Question:** How should the sealed-letter instantiation path seat its single opponent from the scene when the router supplies `npcs_present=[]`, without re-introducing the bystander-leak that motivated skipping the location fallback?

**Recommendation (consult):** Disposition-gate a sealed-letter-specific candidate filter — keep only NPCs whose `disposition.attitude() == HOSTILE`, then let the existing arity validator gate (1 ⇒ seat; 0 or >1 ⇒ loud reject).

**Outcome:** Dev rejected the disposition-gating on verification (see Dev deviation below) — narrator-declared dogfight opponents carry NEUTRAL disposition, so a HOSTILE gate would reject the opponent it must seat and would fail the RED test. The reuse-first fix (relax the guard so the existing category-keyed `_npc_fallback_at_location` runs for sealed-letter, arity-validated) was implemented instead. Architect affirmed this at spec-check.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/dispatch/encounter_lifecycle.py` — relaxed the NPC location-fallback guard so `sealed_letter_lookup` encounters also source their opponent from `snapshot.npcs` at the player's location; the pre-existing arity validator gates it (1 ⇒ seat blue; 0 or >1 ⇒ loud `SealedLetterArityError`). Recorded why disposition-gating was rejected.
- `tests/fixtures/dogfight_playtest_encounter.py` — `make_dogfight_playtest_state` now instantiates via `instantiate_encounter_from_trigger` (the live sync primitive) instead of the removed `_apply_narration_result_to_snapshot` instantiation block.

**Tests:** 4/4 dogfight instantiation targets GREEN (1 RED→green, 2 guards held, 1 smoke repro fixed); 41 encounter/sealed/fallback/opponent regression tests GREEN; full dispatch+integration sweep 198 passed / 0 failed / 33 skipped.

**AC coverage:**
- AC1 — DONE: `test_three_turn_dogfight_resolves_through_production_path` green; encounter seated red+blue via live primitive.
- AC2 — DONE: `snap.encounter` set with both sides; 3-turn resolution + dogfight.* spans green.
- AC3 — DONE: zero-opponent guard returns `sealed_letter_arity_rejected` error payload + span, no phantom seat.
- AC4 — DONE: opponent seated at instantiation via the production primitive; one-sided duel refused (ADR-116).

**Branch:** `feat/59-17-dogfight-instantiation-production-path` (pushed)

**Rework R1 (after Reviewer REJECT):** Replaced the bare guard relaxation with an adversary-filtered sealed-letter fallback (`_npc_is_adversary` + `adversary_only` param). Fixes the Story 45-33 bystander-leak regression. Files changed (R1): `sidequest/server/dispatch/encounter_lifecycle.py`, `tests/server/dispatch/test_dogfight_instantiation_production_path.py` (added `test_dogfight_with_only_a_bystander_present_refuses`). Verified GREEN against the FULL owning module this time: `tests/server/test_encounter_lifecycle.py` (45-33 now green) + `tests/server/dispatch/` + `tests/integration/` = 224 passed / 0 failed / 33 skipped. Pushed (commit 52023f3).

**Handoff:** To spec-check (Architect), then TEA verify.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — all drift pre-logged by TEA and Dev; resolutions sound. No hand-back.
**Mismatches Found:** 4 (3 already logged, 1 deferred finding) — none require Option B.

- **AC1/AC2 name `_apply_narration_result_to_snapshot` as "the production path"** (Different behavior — Architectural, Major-on-paper / Minor-in-effect). Code is router-driven via `instantiate_encounter_from_trigger` (the named block was removed in 59-4/ADR-113). Observable AC met by the now-green smoke test. **Recommendation A — Update spec.** Already logged by TEA + Dev.
- **AC3 names spans `encounter.instantiation_failed` / `encounter.opponent_missing`** (Missing in code — Behavioral, Minor). Real loud signals are `encounter.sealed_letter_arity_rejected` (+ payload) / `encounter.no_opponent_available`. **Recommendation C — Clarify spec.** Contract satisfied; guard test pins it. Already logged by TEA.
- **Dev rejected the green-phase consult's disposition-gating** (vs. consult — Architectural, Minor). Verified: narrator-declared opponents default NEUTRAL (`session.py:1533`), so a HOSTILE gate rejects the opponent it must seat — would have failed RED + live coyote_star. Category + arity is the right, simpler discriminator (reuse-first). **Recommendation A — code is right; affirmed.**
- **>1 adversary at location conservatively refuses** (Known boundary — Behavioral, Minor). Safe + loud; smarter selection needs a hostility signal for neutral NPCs — out of scope. **Recommendation D — Defer.** Dev filed Delivery Finding; no sibling AC depends on it.

**Decision:** Proceed to verify (TEA). Implementation aligns with the *intent* of every AC; mismatches are stale spec text + hypothetical span names — all logged, resolved A/C/D, none warranting a code hand-back.

### Spec-check amendment (rework R1)

The R0 mismatch analysis above stands. The rework (`_npc_is_adversary` + `adversary_only` fallback filter) is reviewed against spec and is **aligned, no new drift**:
- **AC3 / ADR-116 / No-Silent-Fallbacks** — now *more* compliant than R0: a lone bystander is refused loudly (`sealed_letter_arity_rejected`) instead of silently seated. The R0 deviation I affirmed ("category + arity is the right discriminator") was wrong — category is necessary but not sufficient; the Reviewer's catch is correct and the rework's disposition-OR-role predicate is the right discriminator. My R0 affirmation is hereby corrected.
- **AC1/AC2** — unchanged; the hostile-opponent and explicit-opponent paths still seat red/blue (smoke + production-path tests green).
- **New deferred item (Dev R1 Delivery Finding)** — narrator-declared opponents with `npc_role_id=None` + neutral disposition won't seat from the fallback (refuse-loud). **Recommendation D — Defer:** correct safe direction; the fix belongs in narrator/materializer opponent-tagging, not this lifecycle seam. No sibling AC blocks on it.
- The earlier ">1 adversary refuses" boundary is unchanged and still Deferred.

**Spec Alignment (R1):** Aligned. **Decision:** Proceed to verify (TEA).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed — quality-pass gate holds.

Quality gate (no code changed since green): `tests/server/dispatch/` + `tests/integration/` → **198 passed / 0 failed / 33 skipped** (skips are sidequest-content availability guards). Lint clean (`ruff check`) on all three changed files.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`encounter_lifecycle.py`, `dogfight_playtest_encounter.py`, `test_dogfight_instantiation_production_path.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings (high) + 1 (low) | `GameSnapshot(genre=...)`+`genre_slug` init idiom repeated across test/fixture modules; suggests a shared snapshot factory |
| simplify-quality | clean | "separation of concerns is excellent"; fixture uses explicit path, test exercises the fallback seam |
| simplify-efficiency | clean | "well-engineered — one guard relaxation, two protection gates remain"; rejected-alternative comment is justified, not over-engineering |

**Applied:** 0 fixes.
**Flagged / declined (TEA judgment):** the 3 reuse findings. Declined with rationale — they propose extracting a shared factory for a **2-line, idiomatic** pytest snapshot init, and two of the three call sites the refactor would touch are **outside this story's diff** (`test_sealed_letter_dispatch_integration.py` is unchanged by 59-17; `make_dogfight_playtest_state` predates it). Auto-applying would (a) expand the verify commit into unrelated files, (b) add an import/indirection dependency for negligible DRY gain (YAGNI). The low-confidence reuse note itself concluded the engine asymmetry is "load-bearing… code structure is correct."
**Reverted:** 0.

**Overall:** simplify: clean (no fixes warranted; reuse findings declined as out-of-scope micro-DRY).

**Handoff:** To Reviewer (Westley).

## TEA Assessment (verify — rework R1)

**Phase:** finish (R1)
**Status:** GREEN confirmed — quality-pass gate holds.

Quality gate run against the **full owning module** this round (the lesson from the R0 miss): `tests/server/test_encounter_lifecycle.py` + `tests/server/dispatch/` + `tests/integration/` → **218 passed / 0 failed / 33 skipped**. Pyright on `encounter_lifecycle.py`: 4 errors, all pre-existing `reportOptionalMemberAccess` on `.core` (on develop; the `npc: Npc` annotation added 0 new errors). Ruff clean.

### Simplify Report (R1)

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`encounter_lifecycle.py`, `test_dogfight_instantiation_production_path.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | `_npc_is_adversary`, `_ADVERSARIAL_ROLE_IDS`, `adversary_only`, `_seat_bystander` are well-scoped; `_seat_bystander`/`_seat_opponent` mirror is an intentional fixture-builder pattern |
| simplify-quality | 2 med + 2 low | (1) `_npc_is_adversary(npc)` missing annotation; (2) OTEL test asserts span presence not attributes; (3) casing-contract doc; (4) `_seat_opponent` disposition implicit |
| simplify-efficiency | 1 med + 1 low | (1) `_ADVERSARIAL_ROLE_IDS` has 6 tokens, only "hostile" tested (YAGNI); (2) `adversary_only` bool vs passing `resolution_mode` |

**Applied:** 1 fix (high-value, zero-risk) — added `npc: Npc` annotation to `_npc_is_adversary`, matching the file's own convention (`_is_adversarial(category: str)`, `_npc_fallback_at_location(snapshot: GameSnapshot, …)`). Committed `59b6067`; gate re-run green (218/0/33).

**Flagged / declined (TEA judgment):**
- *OTEL span-attribute assertion (quality, med)* — declined: the existing "span fired exactly once" assertion already proves the wiring; adding an attribute-key assertion risks guessing the key and reopening a green test. Noted as a possible future strengthening.
- *Casing-contract doc (quality, low)* — declined: `_npc_is_adversary` already does `.strip().lower()` against an all-lowercase set; self-evident.
- *`_seat_opponent` explicit disposition (quality, low)* — declined: the opponent is **deliberately** neutral-disposition + role="hostile" to model the real narrator case (seated via role, not disposition); setting it hostile would misrepresent the scenario the test exists to cover.
- *Trim `_ADVERSARIAL_ROLE_IDS` to `{"hostile"}` (efficiency, med)* — declined: `npc_role_id` is a **content-authored** field; the synonyms ("enemy"/"opponent"/"adversary"/"rival"/"antagonist") are cheap defensive breadth so real content isn't brittle, and the disposition-HOSTILE branch is the primary production net. Trimming would raise the chance of a real opponent failing to seat. Kept.
- *`adversary_only` bool → `resolution_mode` param (efficiency, low)* — declined: the boolean is the **cleaner** separation of concerns — a location-fallback helper should not import confrontation resolution-mode semantics; the caller computes the mode check and passes intent as a flag. Kept.

**Reverted:** 0.

**Overall:** simplify: applied 1 fix (type annotation); all other findings declined with rationale.

**Handoff:** To Reviewer (Westley) for re-review of the rework.

## Reviewer Assessment

**Verdict:** REJECTED — changes requested. One blocking [HIGH] regression.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | Guard removal lets a lone **bystander** leak into a sealed-letter duel. The pre-existing Story 45-33 regression test `tests/server/test_encounter_lifecycle.py::test_sealed_letter_empty_npcs_present_raises_without_consuming_fallback` now FAILS: with `npcs_present=[]` and one bystander (`npc_role_id="bystander"`) at the location, the fallback seats it as blue, the arity check sees count==1 and passes, so no `ValueError('got 0 npcs_present')` is raised. Confirmed live: `DID NOT RAISE`. This violates ADR-116 ("an Other", not "any warm body") and CLAUDE.md No-Silent-Fallbacks. | `sidequest/server/dispatch/encounter_lifecycle.py:494` (`if not npcs_present:` — the relaxed guard) | The sealed-letter fallback must filter candidates to **genuine adversaries**, not seat every location NPC. The discriminator both tests provide is `npc_role_id` (`"hostile"` ⇒ seat vs `"bystander"` ⇒ skip), NOT disposition (the consult's wrong field) and NOT category (`_is_adversarial` is encounter-level, so it can't tell a bystander from a pilot). A lone bystander must yield 0 candidates ⇒ arity raises "got 0"; a lone hostile must yield 1 ⇒ seats. Keep this sealed-letter-specific — the non-sealed brawl path *intentionally* pulls in all location NPCs and must stay unchanged. This is the Architect consult's "sealed-letter-specific candidate filter" idea, re-keyed off adversarial role/hostility. |

### Why my own green/verify runs missed this
The Dev (me) and TEA-verify test runs scoped to `tests/server/dispatch/` + `tests/integration/`. The 45-33 regression test lives in `tests/server/test_encounter_lifecycle.py` (one directory up) and was never in scope. The full-suite preflight (7335 tests) caught it. Lesson: a guard relaxation must be regression-tested against the *whole* module's existing tests, not just the story's new directory.

### Subagent Results
| # | Subagent | Enabled | Received | Findings | Decision |
|---|----------|---------|----------|----------|----------|
| 1 | reviewer-preflight | yes | Yes | 1 blocking regression (45-33), 5 pre-existing fails (unrelated), 1 cosmetic ruff-format on new test, 1 pre-existing pyright note | **CONFIRMED** — reproduced live (see [TEST]) |
| 2 | reviewer-security | yes | Yes | clean (5 rules checked, 0 violations) | Accepted |
| 3 | reviewer-edge-hunter | no (toggle off) | N/A | — | — |
| 4 | reviewer-silent-failure-hunter | no (toggle off) | N/A | — | — |
| 5 | reviewer-test-analyzer | no (toggle off) | N/A | — | — |
| 6 | reviewer-comment-analyzer | no (toggle off) | N/A | — | — |
| 7 | reviewer-type-design | no (toggle off) | N/A | — | — |
| 8 | reviewer-rule-checker | no (toggle off) | N/A | — | — |

(6 diff-subagents disabled via `workflow.reviewer_subagents`; preflight + security enabled.)

### Observations (dispatch-tagged)
- `[EDGE]` **[HIGH]** The exactly-one-bystander boundary is the unhandled edge: arity catches 0 and >1, but count==1-bystander passes. `encounter_lifecycle.py:494` + arity at `:544`. (Self-found; edge-hunter was disabled — I enumerated the arity boundary manually.)
- `[SILENT]` **[HIGH]** The leak is a *silent* one: a bystander becomes a duel opponent with no error, exactly the failure class No-Silent-Fallbacks forbids. The commit message and code comment both claim "the arity validator is the gate that makes this safe… no silent bystander leak" — that claim is false for count==1. `encounter_lifecycle.py:470-486` (comment) + `:494`.
- `[TEST]` **[HIGH] CONFIRMED** Ran `tests/server/test_encounter_lifecycle.py::test_sealed_letter_empty_npcs_present_raises_without_consuming_fallback` on this branch → FAIL: "DID NOT RAISE ValueError — Expected ValueError('got 0 npcs_present')". The 3 new 59-17 tests are green, but they only cover hostile-opponent and zero-opponent shapes — there is **no** new test for the lone-bystander sealed-letter shape (that gap is why green looked clean; 45-33 is that test and it's red).
- `[DOC]` **[MEDIUM]** The new comment at `encounter_lifecycle.py:470-486` asserts the arity validator prevents the bystander leak. It is now actively misleading — it documents a safety property the code does not have. Must be corrected as part of the fix.
- `[TYPE]` `[VERIFIED]` No type-contract changes — the guard relaxation is a boolean condition edit; `_npc_fallback_at_location` return type `tuple[list, bool]` unchanged; `instantiate_encounter_from_trigger` signature unchanged. Pre-existing pyright `reportOptionalMemberAccess` on `.core` (lines 157-165) is on develop, not introduced here. Evidence: diff `/tmp/59-17-prod-diff.txt` touches only the `if` condition + comments + fixture call-site.
- `[SEC]` `[VERIFIED]` reviewer-security clean — no SQL/regex/deserialization/file-path/network in the diff; NPC data is server-side game state; error payloads are opaque (`sealed_letter_arity_rejected`), no info leak. Evidence: `confrontation.py:134-149` returns generic error strings.
- `[SIMPLE]` `[VERIFIED]` The implementation is minimal (one condition relaxed) — simplify fan-out (verify phase) returned efficiency: clean, quality: clean. No over-engineering. The problem is under-specification (too broad), not complexity.
- `[RULE]` **[HIGH]** Violates CLAUDE.md "No Silent Fallbacks" (rule-checker was disabled; I checked manually). The fix silently substitutes a bystander for an absent adversary instead of failing loudly. Also undercuts ADR-116's "requires an Other" — a bystander is present-but-not-an-adversary.

### Rule Compliance
Enumerated CLAUDE.md (sidequest-server) + python.md lang-review checks against the diff:
- **No Silent Fallbacks** — VIOLATION at `encounter_lifecycle.py:494` (lone-bystander silent seat). Blocking.
- **No Stubbing / No half-wired** — compliant (full path wired; new test exercises the live seam).
- **Silent exception swallowing (python.md #1)** — compliant; `run_confrontation_dispatch` catches `SealedLetterArityError`/`NoOpponentAvailableError` specifically and logs at `warning`. Not bare/broad.
- **Mutable defaults (#2)** — none introduced.
- **Type annotations at boundaries (#3)** — `instantiate_encounter_from_trigger` already annotated; fixture call-site unchanged.
- **Logging level (#4)** — warning for recoverable engagement gaps; correct.
- **Test quality (#6)** — new tests assert on `snap.encounter` state/roles/error payload (non-vacuous); BUT coverage gap: no lone-bystander sealed-letter case (the 45-33 shape). Blocking via [TEST].
- **Unsafe deserialization (#8) / input validation (#11) / ReDoS** — N/A, confirmed absent (security subagent).
- **Async pitfalls (#9)** — fixture now uses the sync primitive `instantiate_encounter_from_trigger`; correct (helper is sync, smoke test is sync). Compliant.

### Devil's Advocate
Assume this code is broken — and it is. The whole fix rests on one load-bearing claim, written verbatim into the comment and the commit message: *"the arity validator is the gate that makes this safe: exactly one location candidate ⇒ seat it as blue; zero or >1 ⇒ keep the loud rejection."* That sentence quietly assumes the only thing at the player's location is either the duel opponent or a crowd. But a space-opera scene is full of count==1 non-combatants: a hangar tech, a comms officer, a rescued hostage, a friendly wingman who just landed. Empty `npcs_present` is the *normal* router reality (it's hardcoded `[]`), so this fallback fires on essentially every router-driven dogfight. The first time a dogfight is declared in a room that happens to contain exactly one bystander, that bystander is conscripted into a lethal sealed-letter duel as "blue" — and the player is now committing maneuvers against the bartender. No error, no log above warning, nothing on the GM panel that says "I substituted a civilian for your enemy." A confused player sees a duel against a name that makes no sense; a malicious player learns they can *force* any lone NPC into a duel just by declaring a dogfight near them, which is a griefing vector against NPCs the narrator wanted protected. The Dev deviation explicitly claimed "the consult's own goal (no silent bystander leak…) is still met by the loud arity refusal" — the devil's advocate is simply that this claim is empirically false, and a four-stories-old test (45-33) was written precisely to nail it down. The disposition-rejection reasoning was sound (neutral opponents are real), but rejecting the *field* was conflated with rejecting the *concept* of an adversarial filter, and the concept is exactly what's needed. The fix is not "re-add the old guard" (that re-breaks 59-17) — it's "filter the sealed-letter fallback to adversarial-role NPCs," which makes both 45-33 and 59-17 pass.

**Handoff:** Back to Dev (Inigo Montoya) for rework (green phase, per the gate's recovery_config). Story 45-33 already provides the RED net, so no new failing test is required to start — Dev fixes `encounter_lifecycle.py:494` so the sealed-letter fallback filters to adversarial-role NPCs (lone bystander ⇒ 0 candidates ⇒ arity raises; lone hostile ⇒ seats), making BOTH 45-33 and the three 59-17 tests green, and corrects the now-false safety comment. Recommended (non-blocking): add a dispatch-level lone-bystander sealed-letter case to `test_dogfight_instantiation_production_path.py` so the gap can't reopen.

## Reviewer Assessment (re-review R1)

**Verdict:** APPROVED. The [HIGH] regression from R0 is fixed; no new Critical/High issues.

The R0 blocker — a lone bystander leaking into a sealed-letter duel — is resolved. Verified the previously-RED Story 45-33 test now PASSES, and the rework introduces zero new failures.

### Subagent Results
| # | Subagent | Enabled | Received | Findings | Decision |
|---|----------|---------|----------|----------|----------|
| 1 | reviewer-preflight | yes | Yes | GREEN; 45-33 PASSES; 0 branch-attributable failures (same 5 pre-existing develop fails); 4 dogfight + 19 lifecycle tests pass; ruff clean; 4 pre-existing pyright | Accepted — regression fixed |
| 2 | reviewer-security | yes | Yes | clean (all rules 0 violations); 1 [LOW] test-isolation note | Accepted; [LOW] logged non-blocking |
| 3–8 | edge/silent/test/comment/type/rule | no (toggle off) | N/A | — | — |

### Observations (dispatch-tagged)
- `[TEST]` `[VERIFIED]` The R0 blocker is fixed — `test_sealed_letter_empty_npcs_present_raises_without_consuming_fallback` PASSES (preflight full run). The full owning module (`test_encounter_lifecycle.py`, 19 tests) + the 4 production-path dogfight tests are green. The new `test_dogfight_with_only_a_bystander_present_refuses` closes the gap at the live dispatch seam. Evidence: preflight GREEN, 0 branch-attributable failures.
- `[EDGE]` `[VERIFIED]` The count==1 boundary that broke R0 is now handled: `_npc_is_adversary` (encounter_lifecycle.py:348-373) filters before arity, so a lone bystander ⇒ 0 candidates ⇒ loud `SealedLetterArityError`; a lone adversary ⇒ 1 ⇒ seated. Evidence: code read + bystander/opponent/zero tests all green.
- `[SILENT]` `[VERIFIED]` No silent leak remains — the predicate returns False for non-adversaries and the caller raises loudly; the previously-false "arity is the gate" comment was corrected (encounter_lifecycle.py:461-491). Evidence: comment + `_npc_is_adversary` docstring now state the conservative refuse-on-ambiguity contract.
- `[TYPE]` `[VERIFIED]` `_npc_is_adversary(npc: Npc)` is annotated (TEA verify fix); `Npc` imported at module top (safe — `GameSnapshot` already loads `session`). Pyright added 0 new errors (4 pre-existing on `.core`). Evidence: pyright re-run, same 4 errors at shifted lines.
- `[SEC]` `[VERIFIED]` reviewer-security clean — no SQL/regex/deserialization/file/network; `npc_role_id`/`disposition` are server-side state; `.strip().lower()` is defensive normalization. Evidence: security subagent rules table, 0 violations.
- `[SIMPLE]` `[LOW]` The `_ADVERSARIAL_ROLE_IDS` set carries 6 tokens where only "hostile" is exercised; efficiency flagged YAGNI. TEA declined (content-authored field; cheap defensive breadth; disposition is the primary net). I concur — keeping synonyms is the safer call for a content-facing allowlist; not a blocker.
- `[DOC]` `[VERIFIED]` The misleading R0 safety comment is corrected, and `_npc_is_adversary` carries a thorough docstring explaining the disposition-OR-role discriminator and the refuse-on-ambiguity stance. Evidence: encounter_lifecycle.py:349-368.
- `[RULE]` `[VERIFIED]` CLAUDE.md "No Silent Fallbacks" now satisfied — the bystander case fails loudly. python.md #3 (annotations) satisfied by the verify fix. #6 (test quality) — new tests assert state + error payload, non-vacuous.
- `[LOW]` (security) The new test module loads `space_opera_pack` module-scoped → mutates the process-wide `_active_thresholds` with no `reset_attitude_thresholds()` teardown. Worker-isolated under `-n auto` (default); harmless in production. Pre-existing fixture pattern (also in `test_sealed_letter_dispatch_integration.py`). Logged as a non-blocking Delivery Finding for future test-hygiene cleanup.

### Rule Compliance
- **No Silent Fallbacks** — now COMPLIANT (was the R0 violation). Lone bystander ⇒ loud `SealedLetterArityError`. Confirmed by test + code.
- **No half-wired** — COMPLIANT; predicate is wired into the live dispatch path (production-path test green).
- **Type annotations (python.md #3)** — COMPLIANT (`npc: Npc` added).
- **Test quality (python.md #6)** — COMPLIANT; non-vacuous assertions; bystander gap closed. Minor test-isolation note logged (LOW).
- **Unsafe deserialization / input validation / ReDoS** — N/A, confirmed absent (security).

### Devil's Advocate
The fix could be wrong in two ways. First, the allowlist: could a real space_opera enemy fail to seat because its `npc_role_id` isn't in `{hostile, enemy, opponent, adversary, rival, antagonist}` and its disposition is neutral? Yes — and that is the **deliberate, safe** failure direction (loud refusal, not a wrong-Other seat), already logged as Dev's forward Delivery Finding (narrator/materializer should tag dogfight opponents hostile). It does not reintroduce the R0 leak and does not fail any test. Second, the threshold global: under serial `-n0`, a prior module could leave non-default attitude bands, skewing the HOSTILE branch. But the bystander rides disposition 0, which is NEUTRAL under any band the validator permits (`hostile_at < friendly_at`, defaults ∓10), and the default suite runs `-n auto` (isolated). Neither failure mode is a correctness or security risk in production. A malicious player can still only *refuse* a duel by lacking an adversary — they cannot conscript a civilian, which was the actual danger. The rework is sound.

**Handoff:** APPROVED → spec-reconcile (Architect), then SM finish. DO NOT merge — SM owns PR creation/merge.

## Subagent Results

Re-review R1. **2 of 8** reviewer subagents enabled via `workflow.reviewer_subagents`; both returned. Disabled (toggle off, not run): reviewer-edge-hunter, reviewer-silent-failure-hunter, reviewer-test-analyzer, reviewer-comment-analyzer, reviewer-type-design, reviewer-rule-checker.

All received: Yes.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | GREEN | 45-33 regression now PASSES; 0 branch-attributable failures (5 pre-existing develop fails unchanged); 4 dogfight + 19 lifecycle tests pass; ruff clean; 4 pre-existing pyright | Accepted — regression fixed |
| 2 | reviewer-security | Yes | clean | 0 rule violations; 1 [LOW] test-isolation note (`_active_thresholds` global not reset by the module-scoped pack fixture) | Accepted; [LOW] logged non-blocking |

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Targeted the router seam, not `_apply_narration_result_to_snapshot`**
  - Spec source: 59-17 session, AC1/AC2 + Confirmed Repro
  - Spec text: "Instantiation path: `_apply_narration_result_to_snapshot` (production path, not test-only)" / "MUST: `snap.encounter` is set ... after instantiation"
  - Implementation: New RED tests drive `run_confrontation_dispatch` (the router-driven live engager) with `npcs_present=[]`, instead of asserting against `_apply_narration_result_to_snapshot`.
  - Rationale: The `_apply_narration_result_to_snapshot` instantiation block was removed in Story 59-4 / ADR-113 (confirmed at `narration_apply.py:2526`). The real production instantiation path is now the router → `run_confrontation_dispatch`. Asserting against the removed path would pin behavior to dead code. The observable AC is preserved — only the entrypoint under test changed to the live one.
  - Severity: minor
  - Forward impact: Dev must ALSO rewire the stale smoke-test fixture for the original repro to go green; see Delivery Findings.
- **Did not write the `encounter.instantiation_failed` / `encounter.opponent_missing` span assertion named in AC3**
  - Spec source: 59-17 session, AC3
  - Spec text: "Span: `encounter.instantiation_failed` or `encounter.opponent_missing` on failure"
  - Implementation: The no-opponent guard asserts on the dispatch error payload (`out.data['error']`) plus the absence of an encounter. The production code's existing failure spans are `encounter.no_opponent_available` / `encounter.sealed_letter_arity_rejected` — the AC's span names do not exist.
  - Rationale: Pinning a test to a span name that doesn't exist would couple the test to a guessed implementation. The error-payload + no-encounter assertion is refactor-stable and proves the no-silent-fallback contract.
  - Severity: minor
  - Forward impact: none — guard test already enforces "loud refusal, not silent no-op".

### Dev (implementation)
- **Rejected the Architect consult's disposition-gating; seated via the existing category-keyed location fallback + arity validator**
  - Spec source: 59-17 session, "Architect Consult (green-phase)" Recommendation B, steps 1–3
  - Spec text: "Keeps **only** NPCs whose `disposition.attitude() == HOSTILE`. A friendly/neutral bystander is never a duel candidate" / "Add a narrow sealed-letter candidate filter alongside `_npc_fallback_at_location`"
  - Implementation: Did NOT add a new disposition-gated filter. Relaxed the existing guard at `encounter_lifecycle.py` so the established `_npc_fallback_at_location` (category-keyed `adversarial` side) runs for `sealed_letter_lookup` too; the pre-existing arity validator is the gate (exactly 1 ⇒ seat as blue; 0 or >1 ⇒ keep the loud `SealedLetterArityError`). No new helper.
  - Rationale: Verified against TEA's RED fixture and production reality — the consult's `disposition.attitude() == HOSTILE` gate is wrong here. TEA's RED opponent (`_seat_opponent`) carries the DEFAULT disposition (0 ⇒ NEUTRAL); a HOSTILE gate would exclude it and the RED test would fail. Not a test defect: only bestiary-materialized creatures default to hostile disposition (`session.py:1533` `disposition=-20 if is_creature`); a narrator-declared dogfight opponent — the live coyote_star case — is NEUTRAL too. Hostility in a dogfight is contextual to the scene, not a stored score, so the `_is_adversarial` CATEGORY check + arity is the correct discriminator. Reuse-first: no new code path, one condition relaxed. The consult's own goal (no silent bystander leak, no phantom opponent) is still met by the loud arity refusal.
  - Severity: minor
  - Forward impact: The >1-candidates-at-location case conservatively trips the arity refusal and the dogfight does not instantiate — safe and loud, but a smarter single-adversary selection is deferred to a future story. Recorded as a Delivery Finding. No sibling-story AC depends on multi-candidate seating.
- **Rewired the fixture via `instantiate_encounter_from_trigger` (sync primitive), not `run_confrontation_dispatch` (async)**
  - Spec source: 59-17 session, TEA handoff "Rewire the stale fixture"
  - Spec text: "must instantiate through the real production path (`run_confrontation_dispatch` / `instantiate_encounter_from_trigger`)"
  - Implementation: `make_dogfight_playtest_state` (a sync helper) now calls `instantiate_encounter_from_trigger` directly with the explicit opponent mention, rather than the async `run_confrontation_dispatch`.
  - Rationale: TEA named both as acceptable. `instantiate_encounter_from_trigger` is the exact sync primitive `run_confrontation_dispatch` delegates to — same instantiation, role tagging, and OTEL — minus the dispatch's try/except that swallows engagement errors. For a fixture that WANTS instantiation to succeed and assert loudly on failure (no-silent-fallbacks), the primitive is correct: it raises instead of returning a swallowed error, and keeps the helper synchronous (the smoke test is sync). The router-with-empty-`npcs_present` path is covered by `test_dogfight_instantiation_production_path.py`.
  - Severity: trivial
  - Forward impact: none — sibling 59-19 consumes `snap.encounter`/`drive_dogfight_turn`, both unchanged.

### Reviewer (audit)
- **TEA: "Targeted the router seam, not `_apply_narration_result_to_snapshot`"** — ACCEPTED. The named path was removed in 59-4/ADR-113; targeting the live router seam is correct. Verified against the diff.
- **TEA: "Did not write the `encounter.instantiation_failed`/`encounter.opponent_missing` span assertion"** — ACCEPTED. Those span names don't exist; asserting on the real error payload + existing spans is refactor-stable.
- **Dev: "Rejected the Architect consult's disposition-gating; seated via the existing category-keyed fallback + arity validator"** — **FLAGGED.** The decision to reject the *disposition field* was sound (narrator-declared opponents are NEUTRAL), but the deviation conflated rejecting the field with rejecting the *concept* of an adversarial candidate filter — and the final clause is factually wrong: "the consult's own goal (no silent bystander leak…) is still met by the loud arity refusal." It is NOT: a lone bystander (count==1) passes arity and is silently seated, breaking the Story 45-33 regression test (confirmed RED on this branch). An adversarial filter IS required; it must key on `npc_role_id` (hostile vs bystander), not disposition and not category. See Reviewer Assessment [HIGH] / [SILENT] / [TEST].
- **Dev: "Rewired the fixture via `instantiate_encounter_from_trigger` (sync primitive)"** — ACCEPTED. The sync primitive is the correct, non-swallowing instantiation entrypoint for a sync fixture; explicit-opponent path is valid and the fallback path is covered by the new test.

### Dev (implementation — rework R1, addressing Reviewer FLAG)
- **Replaced the bare guard relaxation with an adversary-filtered sealed-letter fallback**
  - Spec source: Reviewer Assessment [HIGH] + Architect Consult (green-phase); Story 45-33 invariant
  - Spec text (45-33 test): "the location-scoped fallback must NOT be consulted — even in this degenerate empty path the bystander is not promoted into the duel as a substitute opponent" / `pytest.raises(ValueError, match="got 0 npcs_present")`
  - Implementation: Added `_npc_is_adversary(npc)` (hostile disposition OR `npc_role_id ∈ _ADVERSARIAL_ROLE_IDS`) and an `adversary_only` param on `_npc_fallback_at_location`. Sealed-letter sourcing passes `adversary_only=True`; a lone bystander ⇒ 0 candidates ⇒ loud `SealedLetterArityError('got 0 npcs_present')`; a lone adversary ⇒ 1 ⇒ seated as blue. Non-sealed path unchanged (`adversary_only=False`). Corrected the false "arity validator is the gate" comment. Added `test_dogfight_with_only_a_bystander_present_refuses` (dispatch-level twin of the 45-33 module test).
  - Rationale: This supersedes my flagged R0 reasoning. The Reviewer was right — arity catches 0/>1 but not the count==1 bystander, so an adversarial candidate filter IS required. The discriminator combines disposition (real signal for materialized creatures, default -20) with an `npc_role_id` adversarial allowlist (the signal both 45-33 "bystander" and 59-17 "hostile" tests carry), since narrator-declared opponents can be neutral-disposition. When hostility is ambiguous (None role + neutral) the predicate refuses (loud), never seats (No Silent Fallbacks).
  - Severity: major (fixes a regression of a shipped invariant)
  - Forward impact: A real narrator-declared dogfight opponent that is neither hostile-disposition nor adversarial-roled (e.g. `npc_role_id=None`) will NOT be seated from the fallback and the dogfight will refuse loudly. That is the safe direction, but it means the narrator/materializer should tag dogfight opponents with a hostile role or disposition for the live router path to engage. Logged as a Delivery Finding (Dev R1).

### Reviewer (audit — re-review R1)
- **R0 Dev deviation "Rejected disposition-gating… arity refusal still prevents the leak" (FLAGGED in R0)** — **RESOLVED by R1.** The rework added the adversarial-candidate filter the flag demanded; the false "arity is the gate" claim is corrected in code and superseded by the R1 deviation. Verified: 45-33 now passes. The FLAG stands as the historical record of why R1 was required.
- **Dev R1: "Replaced the bare guard relaxation with an adversary-filtered sealed-letter fallback"** — **ACCEPTED.** Directly implements the Reviewer-required fix. `_npc_is_adversary` (disposition HOSTILE OR adversarial `npc_role_id`) is the correct discriminator for both the 45-33 (bystander⇒skip) and 59-17 (hostile⇒seat) contracts; `adversary_only` keeps the non-sealed path byte-identical (59-13 intact). Forward impact (neutral/None-role narrator opponents refuse loudly) is the safe direction and is logged for narrator-tagging follow-up. Verified against code + green full-module sweep.
- **TEA verify R1: `npc: Npc` annotation** — ACCEPTED. Convention-matching, zero behavior change, 0 new pyright errors.
### Architect (reconcile)

Reviewed all in-flight deviation entries (TEA test-design ×2, Dev implementation ×2, Dev rework-R1 ×1) and the Reviewer audit stamps (R0 + re-review R1). All are accurate, point at real spec sources, quote spec text inline, and carry the full 6-field format. AC accountability: Dev marked AC1–AC4 all DONE; no ACs were deferred or descoped, so the deferral cross-check is a no-op.

One additional spec-vs-implementation divergence not captured in the prior 6-field entries:

- **AC2 describes the resolution mechanism as `opposed_check`, but a dogfight resolves via `sealed_letter_lookup`**
  - Spec source: `.session/59-17-session.md`, AC2 ("Full resolution path verified")
  - Spec text: "**MUST:** Each turn's dispatch_dice_throw or resolution subsystem fires (space_opera uses opposed_check, not simple DC)" and "OTEL spans prove ordering: encounter.created → turn 1 dispatch → ... → encounter.resolved"
  - Implementation: The space_opera `dogfight` confrontation def is `category: combat`, `resolution_mode: sealed_letter_lookup` (`sidequest-content/genre_packs/space_opera/rules.yaml:439-440`). The 3-turn smoke test resolves through the sealed-letter resolver and asserts `dogfight.confrontation_started` / `dogfight.maneuver_committed` (×2) / `dogfight.cell_resolved` spans per turn — not `opposed_check` and not the literal span names AC2 lists (`encounter.created` / `encounter.resolved`).
  - Rationale: AC2's "opposed_check" wording is a spec inaccuracy — it conflates the generic combat resolution path with the dogfight's sealed-letter (commit-reveal) model. The observable intent of AC2 (three turns resolve end-to-end through the production dispatch path, with per-turn mechanical OTEL spans) is fully met by the now-green `test_three_turn_dogfight_resolves_through_production_path`. No code change is warranted; the spec text should be corrected to name the sealed-letter mechanism. (Note: full 3-turn *resolution* depth is sibling Story 59-19's charter; 59-17's charter is instantiation, which is satisfied.)
  - Severity: trivial (spec-text accuracy; no behavioral or code impact)
  - Forward impact: none on 59-17. Sibling 59-19 (dogfight resolution) should treat the dogfight as sealed-letter, not opposed_check, when authoring its resolution assertions.

No other missed deviations. The implementation aligns with the intent of every AC; all divergences are stale/inaccurate spec text (production-path naming, span names, resolution-mechanism wording) plus the well-documented adversary-filter design decision — every one logged and resolved (A/C/D) across the TEA, Dev, and Reviewer entries above.