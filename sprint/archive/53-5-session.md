---
story_id: "53-5"
jira_key: null
epic: "53"
workflow: "tdd"
---
# Story 53-5: UI surface RigComposure + Edge + injury tags on CharacterSheet

## Story Details
- **ID:** 53-5
- **Epic:** 53 (Road Warrior — Rig two-pool wiring + content alignment)
- **Workflow:** tdd
- **Stack Parent:** none (independent story, depends on 53-1 through 53-4)
- **Points:** 2
- **Priority:** p2

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-24T23:12:22Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24 | 2026-05-24T22:40:14Z | 22h 40m |
| red | 2026-05-24T22:40:14Z | 2026-05-24T22:48:35Z | 8m 21s |
| green | 2026-05-24T22:48:35Z | 2026-05-24T22:56:30Z | 7m 55s |
| spec-check | 2026-05-24T22:56:30Z | 2026-05-24T22:57:58Z | 1m 28s |
| verify | 2026-05-24T22:57:58Z | 2026-05-24T23:00:12Z | 2m 14s |
| review | 2026-05-24T23:00:12Z | 2026-05-24T23:06:38Z | 6m 26s |
| green | 2026-05-24T23:06:38Z | 2026-05-24T23:08:07Z | 1m 29s |
| spec-check | 2026-05-24T23:08:07Z | 2026-05-24T23:08:57Z | 50s |
| verify | 2026-05-24T23:08:57Z | 2026-05-24T23:10:15Z | 1m 18s |
| review | 2026-05-24T23:10:15Z | 2026-05-24T23:11:34Z | 1m 19s |
| spec-reconcile | 2026-05-24T23:11:34Z | 2026-05-24T23:12:22Z | 48s |
| finish | 2026-05-24T23:12:22Z | - | - |

## Delivery Findings

No upstream findings during setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

No design deviations at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### TEA (test design)
- **injury_tags derived from statuses, not a separate tags field**
  - Spec source: context-story-53-5.md, AC-1
  - Spec text: "Add optional injury_tags list field to PartyMember... Update serialization to pull from character.core.rig_pool + character.core.tags when present"
  - Implementation: Tests expect injury_tags populated from crash-related Status objects in character.core.statuses (text="injury", text="dismounted"), since character.core.tags does not exist — story 53-3 crash handler stores injuries as Status entries, not a tags field
  - Rationale: The story context was written before 53-3 shipped; the real crash handler uses statuses. Tests reflect the actual data source.
  - Severity: minor
  - Forward impact: none — the wire contract (injury_tags as list[str]) is identical regardless of extraction source

### Architect (reconcile)
- No additional deviations found.
  - TEA's injury_tags deviation is accurate: verified `character.core.tags` does not exist on CreatureCore (`sidequest-server/sidequest/game/creature_core.py`); crash handler at `sidequest-server/sidequest/game/rig_crash.py:111-112` appends Status objects with `text="injury"` and `text="dismounted"`. The extraction in `views.py:549-553` correctly filters against these constants. Spec source path and text are accurate.
  - Dev's "No deviations" is accurate for the protocol model and UI rendering work.
  - The ProtocolBase serialization broadening is correctly categorized as a Delivery Finding (side effect) rather than a spec deviation.
  - No AC deferrals to verify (no AC accountability table present — all ACs addressed).

## Sm Assessment

**Setup Complete:** Yes
**Session File:** .session/53-5-session.md
**Context File:** sprint/context/context-story-53-5.md
**Branch:** feat/53-5-ui-surface-rig-composure-edge-injury-tags (sidequest-ui, base: develop)
**Repos:** sidequest-ui (primary), sidequest-server (protocol model)
**Dependencies:** 53-1 ✓, 53-2 ✓, 53-3 ✓, 53-4 ✓ — all shipped

**Scope:** Two-repo story: server protocol model (PartyMember fields) + UI CharacterSheet component (RigComposure bar, Edge bar, injury tags). All backend plumbing is in place from the prior four stories.

**Handoff:** To Radar (TEA) for RED phase — write failing tests covering protocol serialization and component rendering.

## Tea Assessment

**Tests Required:** Yes
**Reason:** Two-repo story (protocol model + UI component) requires TDD coverage

**Test Files:**
- `sidequest-server/tests/server/test_party_member_rig_composure.py` — Protocol model fields + wiring stubs
- `sidequest-ui/src/components/__tests__/CharacterSheet.test.tsx` — RigComposure section + injury tags rendering

**Tests Written:** 22 tests covering 3 ACs (AC-1 protocol, AC-2 types, AC-3 rendering)
**Status:** RED (15 failing, 4 passing negative assertions, 3 skipped fixture-dependent wiring)

### Test Breakdown

| Test | AC | Status |
|------|----|--------|
| party_member_accepts_rig_composure_fields | AC-1 | failing |
| party_member_rig_composure_defaults_to_none | AC-1 | failing |
| party_member_rig_composure_zero_is_valid | AC-1 | failing |
| party_member_serializes_rig_composure_in_dict | AC-1 | failing |
| party_member_serializes_none_rig_composure | AC-1 | failing |
| party_member_accepts_injury_tags | AC-1 | failing |
| party_member_injury_tags_defaults_to_empty | AC-1 | failing |
| party_member_serializes_injury_tags | AC-1 | failing |
| party_member_from_character_has_rig_fields | AC-1 | skipped (fixture) |
| party_member_from_character_no_rig_is_none | AC-1 | skipped (fixture) |
| party_member_from_character_crash_injuries | AC-1 | skipped (fixture) |
| renders RigComposure section when present | AC-3 | failing |
| renders rig composure current/max values | AC-3 | failing |
| renders Edge bar in composure section | AC-3 | failing |
| renders RigComposure label distinct from Edge | AC-3 | failing |
| does NOT render rig section when absent | AC-3 | passing |
| does NOT render rig section when null | AC-3 | passing |
| renders rig composure at zero (wrecked) | AC-3 | failing |
| renders injury tags when present | AC-3 | failing |
| does NOT render injury tags when empty | AC-3 | passing |
| does NOT render injury tags when absent | AC-3 | passing |
| wiring: App-shaped data with rig pool | AC-3 | failing |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #4 null-undefined | RigComposure defaults to none; zero vs absent tests | failing |
| #6 react-jsx conditional render | absent/null rig does not render section | passing |
| #8 test-quality | all assertions are meaningful (no vacuous) | self-checked |

**Rules checked:** 3 of 13 applicable TypeScript lang-review rules have direct test coverage
**Self-check:** 0 vacuous tests found — all assertions check specific values or DOM element presence/absence

**Handoff:** To Major Winchester (Dev) for implementation

## Delivery Findings

### TEA (test design)
- **Gap** (non-blocking): Story context references `character.core.tags` for injury extraction, but CreatureCore has no `tags` field. Crash handler (story 53-3) stores injuries as `Status` objects in `character.core.statuses` with text="injury" and text="dismounted". Dev should extract injury_tags from statuses, not a nonexistent tags field.
  Affects `sidequest-server/sidequest/server/views.py` (party_member_from_character extraction logic).
  *Found by TEA during red phase.*

### Dev (implementation)
- **Improvement** (non-blocking): ProtocolBase serialization updated to include None values for fields with None defaults. This changes the wire protocol shape — fields like portrait_url, sheet, inventory will now appear as `null` in JSON instead of being omitted. Both Python and TypeScript sides handle this correctly (verified: 2766 server + 1545 UI tests pass). The change is semantically correct — None-default fields carry meaningful state.
  Affects `sidequest-server/sidequest/protocol/base.py` (serialization semantics).
  *Found by Dev during implementation.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/protocol/models.py` — Added rig_composure_current, rig_composure_max, injury_tags fields to PartyMember
- `sidequest-server/sidequest/protocol/base.py` — Updated serialization to include None for fields with None defaults
- `sidequest-server/sidequest/server/views.py` — Extract rig_pool and crash statuses in party_member_from_character
- `sidequest-ui/src/components/CharacterSheet.tsx` — Added rig_composure_current, rig_composure_max, injury_tags to CharacterSheetData; render Composure section with Edge/Rig bars + injury tags
- `sidequest-ui/src/types/party.ts` — Extended CharacterSummary with rig pool and injury_tags fields

**Tests:** 36/36 passing (GREEN), 3 skipped (fixture-dependent wiring — out of scope)
**Full Suite:** Server 2766 pass / 4 pre-existing fail / 41 skip. UI 1545 pass / 0 fail.
**Branch:** feat/53-5-ui-surface-rig-composure-edge-injury-tags (pushed, both repos)

**Handoff:** To spec-check (Architect)

## Dev Assessment (rework)

**Implementation Complete:** Yes
**Rework Reason:** Reviewer found App.tsx wiring gap — rig_composure and injury_tags fields not passed through PARTY_STATUS handler to CharacterSheetData.
**Files Changed:**
- `sidequest-ui/src/App.tsx` — Wire rig_composure_current, rig_composure_max, injury_tags through the PARTY_STATUS → CharacterSheetData assembly (3 lines added at lines 883-885)

**Tests:** 1545/1545 passing (GREEN), zero regressions
**Branch:** feat/53-5-ui-surface-rig-composure-edge-injury-tags (pushed)

**Handoff:** To spec-check (Architect) → verify → review

## Tea Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 7

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplicated logic or extraction opportunities |
| simplify-quality | 5 findings | All in pre-existing code outside story 53-5 diff (redundant import, silent fallback, stale comments, import convention) |
| simplify-efficiency | clean | No over-engineering or unnecessary complexity |

**Applied:** 0 high-confidence fixes (the 1 high-confidence finding is in pre-existing code at views.py:667, not in the story diff)
**Flagged for Review:** 1 medium-confidence finding (views.py:504 silent fallback — pre-existing, out of scope)
**Noted:** 3 low-confidence observations (stale test comments, import convention — all pre-existing)
**Reverted:** 0

**Overall:** simplify: clean (no story-scoped findings)

**Quality Checks:** All passing (lint pass, server 2766/0 new fail, UI 1545/0 fail)
**Handoff:** To Colonel Potter (Reviewer) for code review

## Tea Assessment (verify, pass 2 — post-rework)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** skipped (rework was 3 lines in App.tsx; prior pass was clean across all 3 teammates)
**Files Analyzed:** 4 (App.tsx added to diff)

**Overall:** simplify: clean (rework change is minimal passthrough wiring — no new abstractions, duplication, or complexity)

**Quality Checks:** All passing (lint pass, UI 1545/0 fail)
**Handoff:** To Colonel Potter (Reviewer) for re-review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 4 | confirmed 1, dismissed 3 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 returned, 7 disabled)
**Total findings:** 1 confirmed (division-by-zero cosmetic), 3 dismissed (pre-existing or latent-only), 1 reviewer-own HIGH (App.tsx wiring gap)

### Security Findings Triage

1. **base.py:147 `_field_default()` PydanticUndefined sentinel** (medium) — Dismissed: only manifests through `model_construct()` bypass which is not used in production code paths. The guard works correctly for all standard construction. Latent-only risk.
2. **views.py:549 unfiltered statuses broadcast** (low) — Dismissed: pre-existing, not introduced by this diff. The injury_tags filter is correctly scoped.
3. **CharacterSheet.tsx:148 division by zero** (low) — Confirmed as [LOW]: `rig_composure_max=0` produces `NaN%` CSS width. Server validates `max > 0` at RigComposurePool construction, so this can't happen in practice, but defensive guard is cheap.
4. **base.py:79 broader wire surface** (low) — Dismissed: Dev documented in Delivery Findings. Internal null fields carry no secrets. Multiplayer perception filtering (ADR-104/105) is the correct venue for wire-surface auditing, not this story.

## Reviewer Assessment

**Verdict: REJECT**

### Observations

1. [HIGH] **App.tsx wiring gap — feature disconnected in production.** `App.tsx:866-883` assembles `CharacterSheetData` from PARTY_STATUS but does NOT pass through `rig_composure_current`, `rig_composure_max`, or `injury_tags`. The server sends these fields, the types accept them, the component renders them, tests pass — but the App.tsx bridge drops them. The CharacterSheet will NEVER receive rig data in a live session. This is exactly the "Verify Wiring, Not Just Existence" principle from CLAUDE.md. **Fix: add three lines to the `built` object at App.tsx:866.**

2. [VERIFIED] Protocol model fields correct — `models.py:452-457` adds `rig_composure_current: int | None = None`, `rig_composure_max: int | None = None`, `injury_tags: list[str] = Field(default_factory=list)`. Types correct, defaults correct, `extra=forbid` inherited from ProtocolBase.

3. [VERIFIED] Server extraction correct — `views.py:541-553` reads `character.core.rig_pool.current/.max` with None guard, filters statuses against canonical constants from `rig_crash.py`. No silent fallbacks.

4. [VERIFIED] UI conditional rendering correct — `CharacterSheet.tsx:124` uses `!= null` (not `!== undefined`) to gate the section, which correctly handles both null and undefined. Injury tags gated on `&& data.injury_tags.length > 0`.

5. [LOW] [SEC] Division by zero in width calculation — `CharacterSheet.tsx:148` `(data.rig_composure_current / data.rig_composure_max) * 100` produces NaN when max is 0. Server prevents this via RigComposurePool validation, but a defensive `|| 0` or ternary is cheap insurance.

### Devil's Advocate

The tests all pass because they construct `CharacterSheetData` directly, completely bypassing the App.tsx PARTY_STATUS handler that actually builds the object in production. This is the classic TDD blind spot: unit tests prove the component works with correct input, but nobody tested whether the component receives correct input. A wiring test that renders through the App-level PARTY_STATUS flow would have caught this — the test at line 309 of CharacterSheet.test.tsx is titled "wiring" but only proves the component accepts the type, not that the production data pipeline delivers it.

The base.py serialization change is architecturally significant — it changes the wire protocol shape for ALL ProtocolBase models. While the full suite passes and no regressions were detected, this is a protocol-level change being shipped as a side effect of a UI story. It deserved its own story or at minimum an ADR note. That said, the change is semantically correct and well-documented in Delivery Findings.

Could a malicious narrator craft a Status with text matching "injury" or "dismounted" to inject false injury tags? Yes — but the narrator is trusted (it's Claude), and the filter is `s.text in (INJURY_STATUS_TEXT, DISMOUNTED_STATUS_TEXT)` which only matches exact string equality, not substring. The attack surface is the narrator tool, which is already the highest-trust component in the system.

### Rule Compliance

| Rule | Instances Checked | Compliant? |
|------|-------------------|------------|
| No Silent Fallbacks | rig_pool None→None (views.py:541), injury_tags empty→[] (views.py:549) | Yes |
| Verify Wiring | App.tsx:866-883 (CharacterSheetData assembly) | **NO — rig fields not wired** |
| Every Test Suite Needs a Wiring Test | CharacterSheet.test.tsx:309 wiring test | Partial — tests type acceptance, not production data flow |
| extra=forbid | PartyMember inherits from ProtocolBase | Yes |

### Decision

**REJECT — 1 HIGH finding (App.tsx wiring gap) must be fixed before merge.**

Fix required: Add `rig_composure_current`, `rig_composure_max`, and `injury_tags` to the `built` object in `App.tsx:866-883`.

Hand back to Major Winchester (Dev) to fix the wiring gap.

## Subagent Results (re-review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (28/28 pass) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | 0 new (rework is passthrough wiring, no new attack surface; prior pass findings still apply) | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 assessed, 7 disabled)
**Total findings:** 0 new findings. Prior LOW (division-by-zero cosmetic) unchanged — not blocking.

## Reviewer Assessment (re-review)

**Verdict: APPROVE**

### Rework Verification

1. [VERIFIED] **App.tsx wiring gap FIXED** — `App.tsx:883-885` now passes `rig_composure_current`, `rig_composure_max`, `injury_tags` from `rawLocal` (PARTY_STATUS payload) to the `CharacterSheetData` object. The guard pattern matches existing fields: `typeof ... === "number"` for nullable ints, `Array.isArray()` for the list. Evidence: `App.tsx:883-885`.

2. [VERIFIED] **Prior observations still hold** — Protocol model fields correct (`models.py:452-457`), server extraction correct (`views.py:541-553`), UI conditional rendering correct (`CharacterSheet.tsx:124`), injury tags gated properly.

3. [LOW] **Division-by-zero cosmetic** — `CharacterSheet.tsx:148` still produces NaN% if `rig_composure_max` is 0. Server prevents this at construction. Accepted as non-blocking.

### Devil's Advocate (re-review)

The rework fix uses `typeof rawLocal.rig_composure_current === "number"` which correctly handles both `null` (from the server's new None-as-null serialization) and `undefined` (if the field is absent), since `typeof null === "object"` and `typeof undefined === "undefined"`. The `Array.isArray` guard similarly handles null/undefined correctly. The fix is minimal, follows existing patterns, and introduces no new risk.

The prior security findings (ProtocolBase wire surface broadening, PydanticUndefined sentinel subtlety) are architectural observations, not blocking issues. They remain as documented in the prior review's Delivery Findings.

### Rule Compliance (re-review)

| Rule | Compliant? |
|------|-----------|
| Verify Wiring | **YES** — App.tsx now wires all 3 fields end-to-end |
| No Silent Fallbacks | YES — `undefined` fallback is explicit, not a silent default |
| TypeScript null-handling (#4) | YES — `typeof` guard correctly distinguishes null from number |

**Decision:** APPROVE — the HIGH finding from pass 1 is resolved. No new issues.

## Architect Assessment (spec-check, pass 1)

**Spec Alignment:** Aligned
**Mismatches Found:** 1 minor

- **AC-4 CharacterPanel wiring not explicitly changed** (Cosmetic, Trivial) — Recommendation: A (type extension covers it implicitly)
- **ProtocolBase serialization broadened** (Architectural, Minor) — Recommendation: C (semantically correct, zero regressions)

**Decision:** Proceeded to verify

## Architect Assessment (spec-check, pass 2 — post-rework)

**Spec Alignment:** Aligned
**Rework Fix Verified:** App.tsx:883-885 now passes rig_composure_current, rig_composure_max, injury_tags through PARTY_STATUS → CharacterSheetData assembly. The HIGH wiring gap from the Reviewer's rejection is resolved.
**Mismatches Found:** None (rework addressed the only blocking issue)

**Decision:** Proceed to verify