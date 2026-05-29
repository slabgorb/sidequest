---
story_id: "69-1"
jira_key: null
epic: "69"
workflow: "tdd"
repos:
  - "ui"
---
# Story 69-1: 3D dice camera/scale pull-in + dice-lib wiring audit to real server rolls (ADR-074/075)

## Story Details
- **ID:** 69-1
- **Jira Key:** N/A (no Jira for this project)
- **Epic:** 69 (Gameboard & dice UX polish)
- **Workflow:** tdd
- **Repos:** ui (sidequest-ui)
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-28T14:44:42Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T00:00:00Z | 2026-05-28T14:24:28Z | 14h 24m |
| red | 2026-05-28T14:24:28Z | 2026-05-28T14:30:33Z | 6m 5s |
| green | 2026-05-28T14:30:33Z | 2026-05-28T14:34:57Z | 4m 24s |
| spec-check | 2026-05-28T14:34:57Z | 2026-05-28T14:36:02Z | 1m 5s |
| verify | 2026-05-28T14:36:02Z | 2026-05-28T14:39:39Z | 3m 37s |
| review | 2026-05-28T14:39:39Z | 2026-05-28T14:43:40Z | 4m 1s |
| spec-reconcile | 2026-05-28T14:43:40Z | 2026-05-28T14:44:42Z | 1m 2s |
| finish | 2026-05-28T14:44:42Z | - | - |

## Sm Assessment

Setup complete for 69-1 (ui-only, tdd, 3pt bug, epic 69). Branch
`feat/69-1-3d-dice-camera-pull-in` created off `develop` in sidequest-ui; story
status set to in_progress; epic + story context validated (`context-story-69-1.md`,
8253 bytes). 64-7 was parked (empty branch, no commits, status backlog) to make
room for this redirect; its session is preserved at `.session/64-7-session.md.parked`
with an unresolved BLOCKING TEA finding (stale `test_audit...named_thin_corpora`
needs a server audit-dir-walk or test update) for when it resumes.

Setup surfaced three guardrails for TEA (full detail in Delivery Findings +
context): (1) the live dice renderer is `InlineDiceTray.tsx` mounted inline in
ConfrontationOverlay — `DiceOverlay.tsx`/`DiceSpikePage.tsx` are dead, do not edit
them; (2) the top-down camera is a calibrated constraint (2026-04-24 playtest:
oblique made the up-face ambiguous) — pull-in must preserve face legibility; (3)
faces are already server-authoritative via seed replay, so the "wiring audit" AC is
a proving wiring-test, not a re-wire. Handing to Fezzik (TEA) for RED.

## TEA Assessment

**Tests Required:** Yes
**Reason:** N/A

**Test Files:**
- `sidequest-ui/src/dice/__tests__/InlineDiceTray.focal.test.tsx` — AC1 camera/scale
  pull-in (RED) + AC2 server-authoritative wiring audit (passing characterization).

**Tests Written:** 6 tests covering 2 ACs (4 AC1 + 3 AC2 — guardrail counted under AC1).
**Status:** RED (2 failing AC1 tests ready for Dev; 4 passing = top-down guardrail + AC2 audit)

RED breakdown (confirmed via `npx vitest run`):
- ❌ `renders the dice frame larger than the ~180px baseline` — needs `data-testid="dice-frame"`
  on the frame div and a height > 180.
- ❌ `pulls the camera in tighter than the y=2.4 / fov=42 baseline` — camera must be no
  looser than baseline on both axes and strictly tighter on at least one (smaller `y`
  and/or smaller `fov`).
- ✅ `keeps the camera straight-down (top-down calibration preserved)` — GUARDRAIL, passes
  now; protects against an oblique "pull-in" (Playtest 2026-04-24 up-face ambiguity).
- ✅ AC2 ×3 — spectator die replays from server `seed`+`throw_params` (spy on
  `replayThrowParams`), displayed total/faces are the server's verbatim, and nothing is
  fabricated while a result is pending. These PASS because the tray is already
  server-authoritative (SM audit finding confirmed) — they lock that in so a future change
  can't silently fake a roll client-side.

### Rule Coverage

| Rule (typescript.md) | Test(s) | Status |
|----------------------|---------|--------|
| #6 React/JSX — props/state fidelity | camera-prop capture + result-readout assertions | partial (AC tests) |
| #1 type-safety (no `as any` on camera) | reviewed — Dev must keep camera config typed | review-time gate |

**Rules checked:** Story is a focused UI camera/scale tweak; the live lang-review rubric
(`typescript.md`) runs at Reviewer time on the actual diff. AC tests cover the JSX prop/state
fidelity surface (#6). No artificial rule-tests manufactured for rules the small diff won't touch.
**Self-check:** 0 vacuous tests — every test has a meaningful assertion (no `let _ =`, no
`assert(true)`, no always-None checks).

**Handoff:** To Inigo Montoya (Dev) for GREEN.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (6/6 focal tests; full UI suite green pre-verify)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`InlineDiceTray.tsx`, `InlineDiceTray.focal.test.tsx`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 findings | 3 high (helper dup vs DiceOverlay), 2 medium (test mock/fixture dup) |
| simplify-quality | 2 findings | 2 high (BASELINE_FOV / header comment "should be 50") |
| simplify-efficiency | clean | none |

#### Aggregated findings + decisions

| # | Agent | File:Line | Category | Conf | Decision |
|---|-------|-----------|----------|------|----------|
| 1 | reuse | InlineDiceTray.tsx:174 | dup `formatModifier` vs DiceOverlay | high | **DEFER** |
| 2 | reuse | InlineDiceTray.tsx:182 | dup `outcomeColor`/`outcomeLabel` vs DiceOverlay | high | **DEFER** |
| 3 | reuse | InlineDiceTray.tsx:214 | dup `buildAnnouncement` vs DiceOverlay | high | **DEFER** |
| 4 | reuse | focal.test.tsx:27 | mock dup vs sibling test | med | **DEFER** |
| 5 | reuse | focal.test.tsx:87 | fixture dup vs sibling test | med | **DEFER** |
| 6 | quality | focal.test.tsx:85 | `BASELINE_FOV` "should be 50" | high | **DISMISS** |
| 7 | quality | focal.test.tsx:9 | header comment "fov should be 50" | high | **DISMISS** |

**Applied:** 0 fixes. **Reverted:** 0.

**Decision rationale (verified, not asserted):**
- **DEFER #1–3 (reuse, helper dup):** `git diff develop...HEAD` confirms 69-1 did NOT
  touch `formatModifier`/`outcomeColor`/`outcomeLabel`/`buildAnnouncement` — they
  predate the story on `develop` (3 of them present pre-story). The duplicate twins
  live in `DiceOverlay.tsx`, which is OUT of this story's scope (the retained
  `#dice-spike` dev-route file). Extracting a shared `diceHelpers.ts` is a legitimate
  refactor but is scope creep on a 14-line camera tweak and would touch out-of-scope
  code; the `Fail` color also differs (`#fca5a5` vs `#9ca3af`), so the functions are
  NOT byte-identical — merging needs a design call on the canonical color. Belongs in
  its own story.
- **DEFER #4–5 (reuse, test dup):** per-file mock/fixture re-declaration is the
  established convention in this suite (the sibling `InlineDiceTray.test.tsx` does the
  same) and preserves test isolation; the focal file's camera-capture mock is a
  distinct concern. Medium confidence → not auto-applied per workflow.
- **DISMISS #6–7 (quality, "BASELINE_FOV should be 50"):** INCORRECT finding. Verified
  `git show develop:...InlineDiceTray.tsx` → `fov: 42` pre-69-1, and 69-1 changed no
  `fov:` literal. `BASELINE_FOV=42` correctly captures the immediately-pre-69-1 value
  the test guards against. The comment "FOV 42 (was 50)" refers to an EARLIER story's
  50→42 change, not the pre-69-1 state. Setting it to 50 would make `fov < BASELINE_FOV`
  trivially true (42 < 50 always), weakening the pull-in assertion to a guaranteed pass
  — the opposite of what the test must enforce. No change.

**Overall:** simplify: clean (0 applied — all findings deferred-as-out-of-scope or
dismissed-as-incorrect, with verification above).

**Quality Checks:** GREEN (focal 6/6; full suite 1647/1647 at green exit; lint + tsc clean).
**Handoff:** To Westley (Reviewer) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

Verified the diff (`git diff develop...HEAD`) against both ACs in
`context-story-69-1.md`:
- **AC1 (camera/scale pull-in, legible focal moment, top-down preserved):** the
  frame grows 180→240px and the camera pulls in (y 2.4→2.3) while `position[0]`/
  `position[2]` stay 0 and `rotation` stays `-π/2` — the calibrated straight-down
  view is intact, satisfying the spec's "enlarged and/or reframed so the die fills
  materially more of the view" with both levers. The clip-safety math (visible
  extent ≈1.77 > the ±0.8 tray walls) is sound for a perspective camera at this
  distance/fov.
- **AC2 (wiring audit, displayed==server):** no code change, correctly — the spec
  itself framed this as a "proving wiring-test, not a re-wire." The seed-replay
  path was already authoritative; the new tests lock it. Aligned.

The TEA deviation (pinning both px + camera levers) is a reasonable, documented
test-design choice, not implementation drift. Dev's "no live-browser verification"
finding is a verify-phase action item, not a spec mismatch — flagged for Fezzik.

**Decision:** Proceed to verify (TEA).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/dice/InlineDiceTray.tsx` — frame `<div>` 180px → 240px with
  `data-testid="dice-frame"`; camera `position` y 2.4 → 2.3 (fov unchanged at 42);
  comments updated to document the new framing math and 69-1 rationale.

**Tests:** 6/6 GREEN on `InlineDiceTray.focal.test.tsx`; full UI suite 1647/1647;
lint clean; `tsc --noEmit` exit 0.
**Branch:** feat/69-1-3d-dice-camera-pull-in (pushed)

**Approach:** Minimal change to the two named levers. The dominant legibility win is
the ~33% larger px frame; the camera pull-in (y 2.4 → 2.3) is bounded by clip-safety —
at y=2.3/fov=42 the visible extent is ≈1.77 units, leaving ~0.08 padding past the
±0.8 tray walls so the tumbling die never clips. Top-down calibration (straight-down,
`position[0]==0 && position[2]==0`, `rotation=-π/2`) preserved per the guardrail test.
AC2 required no code change — the tray was already server-authoritative; the audit
tests now lock that in.

**Dead-code note:** SM flagged `DiceOverlay.tsx`/`DiceSpikePage.tsx` as deletion
candidates. Verified they are NOT dead — `DiceSpikePage` is lazy-loaded in
`src/main.tsx:9` as the `#dice-spike` isolated-testing route and imports `DiceOverlay`.
Left intact (deleting would break a live dev route); matches the App.tsx:52 "retained
for isolated testing" comment.

**Handoff:** To verify phase (TEA).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

- **Improvement** (non-blocking): The live dice renderer is `src/dice/InlineDiceTray.tsx`, mounted *inline* in the Confrontation panel (`components/ConfrontationOverlay.tsx:564`). The old `DiceOverlay.tsx` + `DiceSpikePage.tsx` are dead (retained "for isolated testing only" per `App.tsx:52` comment) — grep shows no production consumers. **All camera/scale work belongs in `InlineDiceTray.tsx`, not `DiceOverlay.tsx`.** If Dev confirms zero non-test consumers, delete the dead overlay in the same PR. *Found by SM during setup.*
- **Improvement** (non-blocking): Camera is a **deliberately top-down** frame (`InlineDiceTray.tsx:352-355`, `position:[0,2.4,0]`, `fov:42`) — inline comment records Playtest 2026-04-24 found oblique cameras made the "up" face ambiguous. The "pull-in" must enlarge the frame / tighten distance while *preserving* top-down face legibility; do NOT reintroduce an oblique hero angle without a logged design deviation. *Found by SM during setup.*
- **Improvement** (non-blocking): "Wiring audit to real server rolls" — the tray is *already* server-authoritative: settled faces come from `replayThrowParams(diceResult.throw_params, diceResult.seed)` (`InlineDiceTray.tsx:259`); `randomThrowParams()` is cosmetic toss params only. The AC is to *prove* this end-to-end with a wiring test (no client-RNG face path), not to re-wire. *Found by SM during setup.*

### TEA (test design)
- **Improvement** (non-blocking): AC2 confirmed GREEN at RED time — the spectator seed-replay path and verbatim server total/faces display already work; no rolling-player client-RNG face path leaks into the displayed result. The audit answer is "wiring correct"; AC2 tests are permanent regression locks, not a Dev to-do. Affects `sidequest-ui/src/dice/InlineDiceTray.tsx` (no change needed for AC2). *Found by TEA during test design.*
- **Gap** (non-blocking): the frame `<div>` wrapping the `<Canvas>` (`InlineDiceTray.tsx:327`) has no test handle. The RED test requires Dev to add `data-testid="dice-frame"` to it so frame scale is assertable. Affects `sidequest-ui/src/dice/InlineDiceTray.tsx` (add testid + bump height). *Found by TEA during test design.*

### Dev (implementation)
- **Question** (non-blocking): the change is fully covered by unit tests + clip-safety math, but the 3D roll could NOT be eyeballed in a live browser this phase — the inline tray only renders inside an active confrontation (WebGL is unavailable in jsdom). Recommend a quick visual confirmation during the verify/playtest pass that the enlarged 240px die rolls without clipping at the tray walls. Affects `sidequest-ui/src/dice/InlineDiceTray.tsx` (visual-only confirmation). *Found by Dev during implementation.*
- **Improvement** (non-blocking): `DiceOverlay.tsx`/`DiceSpikePage.tsx` are NOT dead code (SM's deletion candidate) — `DiceSpikePage` is the live `#dice-spike` isolated-testing route (`src/main.tsx:9`). Leaving them intact is correct; the prior "delete dead overlay" suggestion is resolved as not-applicable. Affects `sidequest-ui/src/main.tsx` + `src/dice/DiceOverlay.tsx`,`DiceSpikePage.tsx` (no change). *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking): `InlineDiceTray.tsx` and `DiceOverlay.tsx` carry duplicate dice helpers (`formatModifier`, `outcomeColor`/`outcomeLabel`, `buildAnnouncement`) — pre-existing, not from 69-1. A future cleanup story could extract a shared `src/dice/diceHelpers.ts`; note the `Fail` color differs (`#fca5a5` vs `#9ca3af`), so it needs a design call on the canonical value, not a blind merge. Affects `sidequest-ui/src/dice/InlineDiceTray.tsx` + `DiceOverlay.tsx` (future extraction). *Found by TEA during test verification.*

### Reviewer (code review)
- **Question** (non-blocking): the 240px frame slightly lowers the canvas aspect for a fixed panel-column width; if the Confrontation panel were ever narrower than ~240px the die could clip horizontally at the ±0.8 tray walls during the tumble (unverifiable in jsdom). Confirm visually during the verify/playtest pass. Affects `sidequest-ui/src/dice/InlineDiceTray.tsx` (visual-only confirmation). *Found by Reviewer during code review.*

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (0 smells, 1647 tests green, tsc clean) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings (assessed by Reviewer below) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings (assessed by Reviewer below) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings (assessed by Reviewer below) |
| 7 | reviewer-security | Yes | clean | none (4 rules checked, 0 violations) | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings (covered by verify simplify pass) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings (assessed by Reviewer below) |

**All received:** Yes (2 enabled returned clean; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 1 deferred (pre-existing helper dup, carried as a TEA delivery finding for a future story)

## Reviewer Assessment

**Verdict:** APPROVED

**Diff under review:** `sidequest-ui/src/dice/InlineDiceTray.tsx` (frame 180→240px + `data-testid="dice-frame"`; camera `position` y 2.4→2.3, fov/rotation/up unchanged; comments updated) + new test `src/dice/__tests__/InlineDiceTray.focal.test.tsx`. Two enabled subagents (preflight, security) returned clean; remaining 7 disabled by settings and assessed by me below.

### Rule Compliance (typescript.md + project rules)

- **#1 Type-safety escapes:** No new `as any` in production code. The test file uses `as unknown as` only on `dice`/`spec` fixture literals — the established pattern in the sibling `InlineDiceTray.test.tsx`, test-only, acceptable. Compliant.
- **#6 React/JSX:** No `useEffect`/`useMemo` dependency changes in this diff; camera and frame are static literals. No `key={index}`, no `dangerouslySetInnerHTML`. Compliant.
- **Comment accuracy (CLAUDE.md — comments must not rot):** The updated frame/camera comments match the new literals; I independently verified the clip-safety math — `2·2.3·tan(21°) ≈ 1.766`, half-extent `0.883 > 0.8` wall → `~0.08` padding. Accurate. The retained "FOV 42 (was 50)" line is a correct historical note (develop has fov:42). Compliant.
- **No Silent Fallbacks / No Stubbing:** Direct numeric literal changes; no fallback branch, no stub. Compliant.
- **Server-authoritative state (ADR-074):** No client RNG introduced; displayed roll still flows from `DICE_RESULT` seed replay (confirmed by security scan + AC2 tests). Compliant.

### Observations

1. `[VERIFIED]` Top-down calibration preserved — `InlineDiceTray.tsx:354-355`: `position[0]=0`, `position[2]=0`, `rotation=[-π/2,0,0]`. Satisfies the 2026-04-24 anti-oblique constraint and the guardrail test.
2. `[VERIFIED]` Clip-safety holds — at y=2.3/fov=42 the vertical extent (1.766) still exceeds the 1.6 tray depth; die edge at ±0.8 wall sits inside the 0.883 half-frame. Math in comment is correct.
3. `[VERIFIED]` Test quality (test-analyzer disabled → I checked) — every test in `focal.test.tsx` asserts concrete values (height>180, camera axes, `replayThrowParams` call args, server total/faces). Zero vacuous assertions; `BASELINE_FOV=42` matches develop pre-69-1 (TEA/I verified via `git show`).
4. `[VERIFIED]` `[SEC]` No server-authority regression — reviewer-security returned clean on 4 rules (server-authoritative state, perception firewall ADR-104/105, XSS, no-silent-fallbacks); AC2 tests prove spectator die replays from server seed and totals/faces render verbatim. No client RNG, no info leakage, no `dangerouslySetInnerHTML`.
5. `[VERIFIED]` No code smells — preflight reports 0 `console.log`, 0 `dangerouslySetInnerHTML`, 0 TODOs, 0 test-skips; tsc clean; only a pre-existing App.tsx lint warning outside the diff.
6. `[LOW]` Live-browser visual unconfirmed (Dev-flagged) — the 3D roll renders only in an active confrontation (no WebGL in jsdom). See Devil's Advocate; carried to verify/playtest as a non-blocking visual check.
7. `[LOW]` Pre-existing helper duplication with `DiceOverlay.tsx` — deferred by TEA to a future cleanup story (not introduced here).

### Devil's Advocate

Assume this is broken. The unit tests assert the camera *config object* and the frame's *CSS height*, but neither can prove the die actually renders legibly — jsdom has no WebGL, so the whole 3D path is mocked away. The one substantive risk is horizontal clipping: R3F's `fov` is the *vertical* field of view, so the camera math guarantees the tray fits *vertically* (1.766 > 1.6 depth). Horizontal visible width = vertical_extent × canvas aspect. The frame div only sets `height: 240` and inherits width from the Confrontation panel column. If that column were ever narrower than ~240px, the canvas would become portrait (aspect < 1), the horizontal extent would drop below the 1.6 tray width, and a die bouncing to the ±0.8 wall could clip at the left/right edges during the tumble. Increasing height from 180→240 *reduces* the aspect for any fixed column width, so this change moves slightly toward that failure mode. In practice the Dockview Confrontation panel is comfortably wider than 240px, so this is low-probability — but it is genuinely unverified by the tests. A confused user wouldn't misread anything (the numeric readout and SR announcement are independent of the canvas), and a malicious user has no new surface (no input, no network, no innerHTML). Stressed-filesystem/config concerns are N/A for a pure render tweak. Conclusion: no Critical/High; the only real-world risk is a cosmetic horizontal-clip edge case that the verify/playtest visual check (already flagged by Dev) will catch. Recorded as `[LOW]`, non-blocking.

**Data flow traced:** server `DICE_RESULT` → `App.tsx` `diceResult` → `GameBoard` → `ConfrontationOverlay` → `InlineDiceTray` → seed-replayed scene + verbatim readout. The diff touches only the presentation frame/camera, not this flow. Safe.

**Pattern observed:** static, well-commented camera/style config at `InlineDiceTray.tsx:328-360` — consistent with the existing component style.

**Error handling:** no new failure paths; the change is declarative render config.

**Handoff:** To Vizzini (SM) for finish-story.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Pull-in pinned to two concrete levers (frame px + camera framing)**
  - Spec source: context-story-69-1.md, AC-1 ("camera/scale pull-in so a roll is a legible focal moment")
  - Spec text: "the inline tray frame is enlarged and/or the camera reframed so the settled die fills materially more of the view"
  - Implementation: tests require BOTH a frame height > 180px AND a camera no looser than y=2.4/fov=42 with strict tightening on at least one axis (rather than accepting either lever alone).
  - Rationale: "camera/scale" names both levers; requiring both gives Dev a concrete, non-arbitrary GREEN bar and prevents a no-op "pull-in" that nudges one axis trivially. Dev may satisfy the camera clause via smaller `y` OR smaller `fov` (flexible). A pull-in achieved purely via `D20_RADIUS` in `@local/dice-lib` is out of this story's scope and would not turn these tests green.
  - Severity: minor
  - Forward impact: if Keith/UX prefer a single-lever or radius-based pull-in, Dev logs a counter-deviation and adjusts the camera test bar.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **TEA — "Pull-in pinned to two concrete levers"** → ✓ ACCEPTED by Reviewer: pinning frame px + camera (with y-or-fov flexibility) is a sound, non-arbitrary GREEN bar faithful to AC1's "camera/scale" wording; Dev satisfied it via y 2.4→2.3 within the allowed envelope.
- **Dev — "No deviations from spec"** → ✓ ACCEPTED by Reviewer: confirmed against the diff — implementation matches the test contract and story scope exactly; no undocumented divergence found.

### Architect (reconcile)
Reviewed the TEA and Dev deviation entries against the spec sources: the one TEA
entry cites a real path (`sprint/context/context-story-69-1.md`, AC-1), quotes the AC
accurately, all 6 fields are present and substantive, and its "Implementation"/"Forward
impact" match what the code and tests actually do. Dev's "No deviations" is accurate —
the diff (frame 180→240px, camera y 2.4→2.3, fov/rotation/up unchanged) matches the
test contract and story scope exactly. No ACs were deferred or descoped (AC1 + AC2 both
DONE), so AC-deferral verification is a no-op. The simplify "DEFER" rows are
code-quality deferrals (pre-existing helper duplication), not spec deviations, and are
correctly carried as delivery findings for a future cleanup story rather than logged as
deviations here.

- No additional deviations found.