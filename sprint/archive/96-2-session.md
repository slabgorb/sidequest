---
story_id: "96-2"
jira_key: ""
epic: "96"
workflow: "tdd"
---
# Story 96-2: Fix Earthman race-boon tier leak — world-tier trait applied at genre tier (source=Race)

## Story Details
- **ID:** 96-2
- **Jira Key:** (none — no Jira for this project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-server
- **Points:** 3
- **Priority:** p2
- **Type:** bug

## Story Context

The Earthman race-boon is applied at genre tier (source=Race) when it should be a world-tier trait (Barsoom world content). This is a tier leak that violates ADR-140 (genre=rulebook / world owns cast+catalog).

**Guard test:** `test_earthman_boon_is_world_tier_not_engine_hardcode` is deliberately RED.

**Epic context:** Follow-up from epic 94 (ADR-140 genre/world boundary). Epic 96-1 (content-coupled test fixture decoupling) landed PR #779; this story fixes the actual tier leak.

## Workflow Tracking

**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-10T00:01:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-09T20:00:00Z | 2026-06-10T00:01:32Z | 4h 1m |
| red | 2026-06-10T00:01:32Z | - | - |

## Branch Strategy

**Branch Strategy:** gitflow (feat/96-2-earthman-boon-tier-leak)
**Subrepo:** sidequest-server (feature branch off develop)

## Sm Assessment

Setup complete and verified. Story 96-2 is a 3-point p2 bug (tdd workflow) in sidequest-server only: the Earthman race-boon — barsoom world content — is applied at genre tier with `source=Race`, violating ADR-140 (genre is the rulebook; the world owns cast and catalog). A guard test, `test_earthman_boon_is_world_tier_not_engine_hardcode`, was deliberately left RED by epic 94 to pin the desired invariant — TEA should start by running it and confirming it fails for the documented reason, then build out any additional RED coverage around the world-tier resolution seam.

Artifacts verified:
- Session file at `.session/96-2-session.md` (canonical location, not the archive misfile)
- Story context at `sprint/context/context-story-96-2.md`
- Feature branch `feat/96-2-earthman-boon-tier-leak` checked out in sidequest-server off develop
- Sprint YAML status set to in_progress
- Jira explicitly skipped — this project has no Jira; sprint YAML is the tracker

Routing: phased tdd → next phase `red`, owner TEA (Fezzik).

## TEA Assessment

**Tests Required:** No
**Reason:** STALE PREMISE — the bug this story describes was already fixed, and the guard test the epic cites is GREEN, not RED.

**Evidence chain (measured, not asserted):**
1. The cited guard test `tests/integration/test_barsoom_chargen.py::test_earthman_boon_is_world_tier_not_engine_hardcode` **PASSES** on current `develop` (server `dde86cc7`) + current content (`71301e6`). Verified twice via testing-runner (RUN_IDs `96-2-tea-red` and `96-2-tea-red-recheck`, the second after fast-forwarding sidequest-content 4 commits): **6 passed, 0 failed, 0 skipped** — including the full positive/negative pair (barsoom Earthman gets STR edge + Race-source leap ability + `chargen.origin_trait.applied` OTEL event; native and non-barsoom/evropi builds get none of it).
2. The fix landed in server commit `5e0f83ef` — `feat(89-5): world-tier origin trait seam + WWN cast gate fix` (2026-06-05 18:32), **46 minutes after** the RED guard test was written (`61efedc1`, 2026-06-05 17:46). The seam (`builder.py:2507`) consumes `acc.origin_trait` from the world `char_creation.yaml` choice content; the commit message explicitly states "never keyed off the race string in engine code."
3. No engine hardcode remains: the only "Earthman" occurrence in `sidequest/` production code is a comment (`builder.py:2503`). The trait definition lives in `genre_packs/heavy_metal/worlds/barsoom/char_creation.yaml` (world tier), per ADR-140.
4. Epic 96 was filed 2026-06-07 04:52 (orchestrator `fee94f05`) — two days after the fix — so the "guard test deliberately left RED" claim was already false at filing; it was carried over from epic 94's notes without re-running the test. (Same stale-premise pattern as 59-18/61-14.)
5. The guard test is not vacuous: it walks evropi (a real non-barsoom heavy_metal world) through the production builder, injects `race_hint="Earthman"`, asserts the race sticks, and asserts no boon/no STR edge/no OTEL event — an engine race-string hardcode would fail it, and the passing positive sibling proves the boon does fire where the world content defines it.

**Tests Written:** 0 — writing artificially failing tests for correct, already-guarded behavior would violate TDD discipline.

### Rule Coverage
Not applicable — no code change is required, so no new rule-enforcement tests. The existing 6-test barsoom chargen suite (89-5) already covers the invariant this story names, including the OTEL lie-detector contract.

**Status:** Cannot reach RED — target behavior is already implemented and green.
**Recommendation:** Close 96-2 as already-done (delivered by 89-5 / server `5e0f83ef`; guard hardened by #761). No Dev work exists. Hand back to SM for disposition, not to Dev.

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (blocking): Story 96-2's premise is stale — the Earthman race-boon tier leak was fixed by 89-5 (server `5e0f83ef`, 2026-06-05) and the cited guard test `test_earthman_boon_is_world_tier_not_engine_hardcode` passes on current develop + content; there is no RED state to hand to Dev. Affects `sprint/epic-96.yaml` (story 96-2 should be closed as already-done and the epic description's "deliberately left RED" claim corrected). *Found by TEA during test design.*

## Design Deviations

None logged at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **No RED tests written — story premise stale**
  - Spec source: sprint/epic-96.yaml, story 96-2 description ("guard test test_earthman_boon_is_world_tier_not_engine_hardcode deliberately left RED")
  - Spec text: "The Earthman race-boon is applied at genre tier (source=Race) when it is barsoom world content — a real tier leak; guard test ... deliberately left RED."
  - Implementation: Zero new tests; verified the cited guard test (and its 5 siblings) is GREEN on current develop + current content via testing-runner, twice.
  - Rationale: The leak was fixed by 89-5 (server commit 5e0f83ef, 2026-06-05 18:32) before epic 96 was filed (2026-06-07). Writing a failing test for already-correct, already-guarded behavior is impossible without asserting falsehoods; TDD policy forbids fake RED.
  - Severity: major (story cannot proceed through red→green; needs SM disposition)
  - Forward impact: 96-2 should be closed as already-done; epic 96 description needs its stale claim corrected.