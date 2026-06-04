---
story_id: "85-1"
jira_key: ""
epic: "85"
workflow: "tdd"
---
# Story 85-1: Confrontation panel legibility & layout pass — readable dial, beat-caption fits its card, kill the dead-space/floating-die

## Story Details
- **ID:** 85-1
- **Jira Key:** (no Jira integration)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T14:57:53Z
**Round-Trip Count:** 1
**Repos:** ui
**Branch:** feat/85-1-confrontation-panel-legibility

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T16:00:00Z | 2026-06-04T14:04:27Z | -6933s |
| red | 2026-06-04T14:04:27Z | 2026-06-04T14:17:18Z | 12m 51s |
| green | 2026-06-04T14:17:18Z | 2026-06-04T14:27:38Z | 10m 20s |
| review | 2026-06-04T14:27:38Z | 2026-06-04T14:37:11Z | 9m 33s |
| red | 2026-06-04T14:37:11Z | 2026-06-04T14:44:33Z | 7m 22s |
| green | 2026-06-04T14:44:33Z | 2026-06-04T14:51:34Z | 7m 1s |
| review | 2026-06-04T14:51:34Z | 2026-06-04T14:57:53Z | 6m 19s |
| finish | 2026-06-04T14:57:53Z | - | - |

## Acceptance Criteria

1. **A1 — Dial as headline:** Promote the two dials to a single tug-of-war scoreboard (YOU fills from left, THEM from right toward center), large tabular numerals, and a VISIBLE empty-track color so THEM 0/10 is not dark-on-dark (WCAG AA 4.5:1 on title + numerals). Closes L162 defect 1.

2. **A2 — BeatGrid layout:** Change gridTemplateColumns from auto-fill → auto-fit so tiles stretch to fill the row instead of huddling left with phantom empty columns.

3. **A3 — Die anchor to beat:** Roll in the clicked tile's own row (tile expands to show rolled N vs DC M → tier); retire or shrink the disconnected fixed 200px die lane so beat→roll→result is one spatial unit. Closes L162 defect 3.

4. **A4 — Beat caption wrapping:** Beat caption wraps INSIDE its tile (or moves to title/▾ expand); never overflows the right edge. Closes L162 defect 2.

5. **A5 — Beat history ledger:** Reclaim the freed right space as a 3-line beat-history ledger (actor · beat · roll vs DC · dial Δ) so dial movement has visible mechanical provenance (mechanics-first players).

6. **Accessibility:** Beat tiles keyboard-reachable in DOM order with visible focus ring; locked-Enter state has an aria-live hint; resolution beat (e.g. Refuse the Premise ✦) carries a distinct role/label, not just an amber border; die/dial animations respect prefers-reduced-motion.

## Story Context

**Epic:** 85 — Post-Playtest UX Polish — Confrontation Panel & Location Surface

**Component:** ConfrontationOverlay strip (sidequest-ui)

**Design Reference:** docs/design/confrontation-space-usage.md (Tier A)

**Closes:** Playtest L162 (sq-playtest-pingpong 2026-06-04)

**Scope:** Pure UI changes to ConfrontationOverlay (React/TypeScript). No protocol change.

**Player Impact:** Mechanics-first players (Sebastien, Jade) rely on reading the dial numerals and beat-roll mechanics directly in the player UI. This story makes those surfaces legible and properly spaced.

## Sm Assessment

Setup complete and ready for the RED phase. Findings:

- **Scope is clean and bounded.** Pure UI change to the `ConfrontationOverlay` strip in sidequest-ui — no protocol change, no server/daemon/content involvement. Single-repo (`ui`), 3pts, tdd. Branch `feat/85-1-confrontation-panel-legibility` created off `develop`.
- **Design is already specified.** `docs/design/confrontation-space-usage.md` (Tier A) is the authoritative spec; the 6 ACs in this session map directly to it (scoreboard dial, auto-fit BeatGrid, die-anchored-to-beat, in-tile caption wrapping, beat-history ledger, accessibility). TEA should write failing tests against these ACs against the existing overlay component, not invent new behavior.
- **Player-facing legibility is the point.** ACs A1/A3/A5 expose dial numerals and beat-roll mechanics in the player UI — directly serves the mechanics-first players (Sebastien, Jade) per the audience rubric. WCAG AA contrast (A1) and prefers-reduced-motion / keyboard reachability (Accessibility AC) are testable, not aspirational.
- **No protocol/contract risk.** Because there's no message-shape change, RED tests are component/render-level (Vitest + Testing Library on the existing overlay), not integration-against-server.

Routing to TEA (the Caterpillar) for the RED phase. No blockers, no Jira (not configured for this project).

## TEA Assessment

**Tests Required:** Yes
**Reason:** Pure-UI render/layout change with 6 testable ACs (visual structure +
accessibility). Vitest + React Testing Library, structural-proxy assertions per the
story-context "Assumptions" (jsdom does not lay out or compute contrast, so data-testid
contracts, Tailwind utility classes, DOM containment, and accessible attributes stand in
for the visual outcomes).

**Test Files:**
- `sidequest-ui/src/components/__tests__/ConfrontationOverlay.spacepass.test.tsx` — new,
  13 tests across 6 describe blocks (A1 dial scoreboard ×3, A2 auto-fit ×1, A3 die anchor
  ×2, A4 caption wrap ×1, A5 beat-history ledger ×2, Accessibility ×4).

**Tests Written:** 13 tests covering all 6 ACs.
**Status:** RED — 13/13 failing. File compiles cleanly (no TS/import errors). Verified via
`testing-runner` (RUN_ID 85-1-tea-red + 85-1-tea-red-detail). Every failure is the INTENDED
assertion, not a render crash. Verbatim confirmations of the four independent (non-testid-gated)
failures:
- A4 truncate: `expected 'text-[13px] truncate min-w-0 …' not to match /\btruncate\b/`
- a11y focus ring: `expected 'relative text-left cursor-pointer …' to match /focus(-visible)?:/`
- a11y aria-live: `expected null not to be null` (`querySelector('[aria-live]')` → null)
- a11y resolution label: `expected 'Refuse the Premise (WILL)' to match /resolution|finisher/i`

The testid-gated tests (A1 `dial-scoreboard`, A3 `beat-roll-anchor`, A5 `beat-history-ledger`)
fail with `Unable to find an element by: [data-testid=…]` — correct RED for seams Dev must add.

**The RED→GREEN contract (new seams Dev introduces):**
- `data-testid="dial-scoreboard"` — bidirectional tug-of-war dial headline; both numerals
  rendered, promoted out of `text-[9px]`/`text-[10px]`, THEM 0/10 on a visible (non-`bg-muted`)
  empty track.
- `beat-grid` inline `gridTemplateColumns` → `repeat(auto-fit, minmax(150px, 1fr))`.
- `data-testid="beat-roll-anchor"` — roll result rendered within the committed tile's row;
  the standalone `width:200px` die lane retired.
- beat label allowed to wrap (drop `truncate`/`whitespace-nowrap` on the label).
- `data-testid="beat-history-ledger"` — exposes the dial delta (see Deviation D1 re: data source).
- beat tile gains a `focus`/`focus-visible` ring; an `aria-live` region carries a
  "pick a beat" hint; resolution button `aria-label` includes "resolution"/"finisher";
  dial animation carries a `motion-reduce:` guard.

### Rule Coverage

Language: TypeScript/React (`.pennyfarthing/gates/lang-review/typescript.md`). This is a
render-only cosmetic change; most rubric rules (validated constructors, enum exhaustiveness,
type-predicate validation, `as any`) are N/A. Applicable rules and their disposition:

| Rule | Test(s) | Status |
|------|---------|--------|
| React §`key={index}` on reorderable lists | (deferred — ledger rows don't exist yet) | review-time |
| React §`useEffect` missing/object-literal deps | (deferred — accumulator not yet written) | review-time |
| a11y: keyboard-reachable commit path + focus ring | `gives each beat tile a visible focus ring` | failing |
| a11y: announced locked state | `announces the locked-commit state via an aria-live hint` | failing |
| a11y: non-colour-only semantics | `labels the resolution beat distinctly, not by colour alone` | failing |
| a11y: prefers-reduced-motion | `guards the dial animation behind prefers-reduced-motion` | failing |

**Rules checked:** the testable rubric rules for a render-only diff (the a11y set) all have
coverage. The two React-hooks rules (`key={index}`, `useEffect` deps) become live ONLY if Dev
implements the A5 ledger via a client-side history accumulator — they are not pre-testable
against code that doesn't exist, so they are flagged here for the Reviewer (Queen of Hearts)
to check against the actual implementation.
**Self-check:** 0 vacuous tests. Every test has a meaningful assertion; the one conditional
test (reduced-motion) asserts a guard IF an animated node exists and `toBeNull()` otherwise —
both branches are meaningful, neither is `assert(true)`.

**Handoff:** To Dev (the White Rabbit) for GREEN implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/components/ConfrontationOverlay.tsx` — the full Tier-A space pass, all
  changes internal to this one component (no protocol/payload change):
  - **A1** `StatusLine` outer div gains `data-testid="dial-scoreboard"` (the dial headline);
    `EdgeBar` numerals promoted from `text-[10px] text-muted-foreground` → `text-sm
    font-semibold text-foreground tabular-nums` so THEM 0/10 is legible, not dark-on-dark. The
    existing `EdgeBar`/`metric-bar`/`metric-bar-fill`/`dual-dial-bars` structure is preserved
    (22 wiring + 3 momentum-sync tests still green).
  - **A2** `BeatGrid` `gridTemplateColumns` `auto-fill` → `auto-fit` (kept `minmax(150px, 1fr)`).
  - **A3** Retired the fixed `width:200px` side lane. The commit row is now stacked
    (`flex-col`); `InlineDiceTray` lives in a `data-testid="beat-roll-anchor"` below the grid,
    in the beats' own column flow, captioned with the committed beat (`▸ {label}`) via new
    `committedBeatId` state. Tray still renders when wired (`onDiceThrow && playerId`), so the
    `inline-dice-tray` host contract is intact.
  - **A4** Beat label `truncate` → `min-w-0 break-words` (caption wraps in-tile, never clips).
  - **A5** New `BeatHistoryLedger` (`data-testid="beat-history-ledger"`) renders the
    most-recent impact's provenance per side (`You/Them · summary · Δ±n`) — see Deviation D2.
  - **Accessibility** Beat tile gains `focus-visible:ring-2`; a polite `aria-live` "Pick a beat
    to commit." hint announces the locked-Enter state; the resolution beat's `aria-label` now
    includes "resolution beat"; `motion-reduce:` guards added to the dial fill + tile transitions.

**Tests:** 111/111 passing (GREEN) across the full confrontation + dice surface — new
`ConfrontationOverlay.spacepass.test.tsx` 13/13, plus 98 pre-existing tests (zero regressions).
Verified via `testing-runner` (RUN_ID 85-1-dev-green). `tsc --noEmit` clean. ESLint clean.
**Branch:** feat/85-1-confrontation-panel-legibility (pushed)

**Handoff:** To Reviewer (the Queen of Hearts).

## Delivery Findings

<!-- Append-only. Each agent adds under its own subheading. -->

### TEA (test design)
- **Gap** (non-blocking): AC5's "3-line ledger of `actor · beat · roll vs DC · dial Δ`" cannot
  be fully fed from the current `CONFRONTATION` payload. `ConfrontationData` carries only a
  SINGLE `last_beat_impact` (+ `opponent_last_beat_impact`), and `BeatImpactView`
  (`effect · dial_moved · summary · own · opponent · resolution · tag`) has **no roll, no DC,
  no actor name, and no history array**. Affects
  `sidequest-ui/src/components/ConfrontationOverlay.tsx` (and the payload type) — the ledger
  needs either a CLIENT-SIDE accumulator (pure-UI: capture beat label on `onBeatSelect`, DC is
  already derivable per-tile as `10 + 2*|base|` clamped 10..30, roll from `diceResult`, dial Δ
  from the next `last_beat_impact`) OR a new `beat_history[]` payload field (which would cross
  into 85-3 / a protocol change). The RED test asserts only what is feedable in pure-UI today
  (ledger region renders + shows the dial Δ from `last_beat_impact`). *Found by TEA during test design.*
- **Improvement** (non-blocking): L162 defect 2 ("caption overflows its card") was diagnosed
  against an italic FLAVOR caption that was already removed on 2026-05-26 (see
  `ConfrontationOverlay.tsx:486-489`). Current code uses `truncate` (clip+ellipsis+nowrap) on
  the label/kind/risk text, so it no longer *overflows* — it *clips*. AC4's real remaining
  intent is therefore "let the caption WRAP and be readable," not "stop it overflowing." The
  A4 test enforces wrapping (rejects `truncate` on the label). Affects
  `sidequest-ui/src/components/ConfrontationOverlay.tsx` `BeatTile`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): A5 would land at full fidelity ("3-line `actor · beat ·
  roll vs DC · dial Δ`") with a small server-side add — a `beat_history[]` array on the
  `CONFRONTATION` payload carrying, per committed beat, the actor, the rolled value, the DC,
  and the dial Δ. The client already derives DC per beat (`10 + 2*|base|`, clamped 10..30) and
  has the roll in `diceResult`, but it has no durable per-beat history and no actor on
  `BeatImpactView`. Affects `sidequest-server` confrontation payload builder + the
  `ConfrontationData`/`BeatImpactView` types in
  `sidequest-ui/src/components/ConfrontationOverlay.tsx`. Natural home: Story 85-3.
  *Found by Dev during implementation.*
- **Question** (non-blocking): `BeatHistoryLedger` and the pre-existing `BeatImpactPanel` both
  key off `last_beat_impact` and now render together — the panel as the "what just resolved"
  callout, the ledger as the Δ-provenance row. They are complementary, not duplicative, but the
  Reviewer should confirm the doubled surface reads well in the strip and isn't visually
  redundant. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx`.
  *Found by Dev during implementation.*

### Reviewer (code review)
- **Bug** (blocking): `BeatHistoryLedger` "Them" row shows the WRONG dial delta — `LedgerRow`'s
  `side === "Them"` branch reads `impact.opponent` (the opponent's cross-effect on the player's
  dial, typically 0) where it must read `impact.own` (the opponent's OWN dial delta). The impact
  object passed for the Them row is already `opponent_last_beat_impact`, whose `.own` is the
  opponent's progress — exactly what `BeatImpactPanel` renders (`opponent.own`) and what the
  Story 73-7 contract pins. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx`
  `LedgerRow` (~line 575). *Found by Reviewer during code review.*
- **Gap** (blocking): the A3 test does not verify its AC. `beat-roll-anchor` renders
  unconditionally on `onDiceThrow && playerId`, so the `fireEvent.click` is inert — the test
  passes whether or not the die is anchored to the committed beat. Affects
  `sidequest-ui/src/components/__tests__/ConfrontationOverlay.spacepass.test.tsx:160`
  (assert the committed beat label renders inside the anchor). *Found by Reviewer during code review.*
- **Gap** (non-blocking): no test exercises the ledger "Them" row — the exact path that hid the
  blocking bug above. Affects the spacepass suite (add an opponent-impact ledger case asserting
  Them Δ = `opponent_last_beat_impact.own`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): pre-existing — the main-component docstring still claims "The ▾
  chevron on each tile reserves the slot for the upcoming expand-for-details feature," but no
  chevron is rendered. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx` docstring.
  *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- **AC5 ledger tested at reduced fidelity vs. the literal AC text**
  - Spec source: context-story-85-1.md, AC5 / design doc A5
  - Spec text: "a 3-line beat-history ledger (`actor · beat · roll vs DC · dial Δ`) so dial
    movement has visible mechanical provenance"
  - Implementation: RED tests assert the ledger REGION renders and shows the dial delta from
    `last_beat_impact`; they do NOT assert 3 rows, the roll-vs-DC column, or the actor column,
    because the current payload carries only a single impact with no roll/DC/actor/history (see
    Delivery Finding above).
  - Rationale: writing tests that demand 3 rows + roll/DC/actor would force a payload/protocol
    change, which is explicitly out of scope for 85-1 (pure UI) and belongs to 85-3. Testing
    only the pure-UI-feedable subset keeps RED honest and satisfiable without a server change.
  - Severity: minor
  - Forward impact: Dev should either build the client-side accumulator (preferred, keeps
    85-1 pure-UI) or escalate the full-fidelity ledger to 85-3. Reviewer should confirm which
    path was taken and that any accumulator obeys the React `key`/`useEffect` rules.
- **Wiring test renders ConfrontationOverlay directly, not a mounted GameBoard (rework round 1)**
  - Spec source: Reviewer finding [RULE A4] / CLAUDE.md "Every Test Suite Needs a Wiring Test"
  - Spec text: "at least one integration test that verifies the component is ... reachable from
    production code paths" (Reviewer suggested mounting `<GameBoard …/>`).
  - Implementation: the new wiring test renders the real `ConfrontationOverlay` through
    GameBoard's exact prop surface (data + onBeatSelect + dice wiring + last_beat_impact) and
    asserts all five seams co-render — it does NOT mount `GameBoard`.
  - Rationale: no test in the repo mounts `GameBoard` (heavy dockview + providers + hooks);
    doing so for a cosmetic story is disproportionate and brittle. Production wiring IS verified
    (rule-checker confirmed `GameBoard.tsx:543` renders the component); the test pins that the
    new seams sit on that component's live render path, matching the repo's established wiring
    idiom (`src/__tests__/confrontation-wiring.test.tsx`, which also renders the component directly).
  - Severity: minor
  - Forward impact: if a true end-to-end GameBoard-mount harness is later built, fold this in.

### Dev (implementation)
- **A5 ledger renders the most-recent impact per side, not a 3-row roll-vs-DC history**
  - Spec source: context-story-85-1.md, AC5 / design doc A5
  - Spec text: "a 3-line beat-history ledger (`actor · beat · roll vs DC · dial Δ`) so dial
    movement has visible mechanical provenance"
  - Implementation: `BeatHistoryLedger` renders the available `last_beat_impact` (+
    `opponent_last_beat_impact`) as `You/Them · summary · Δ±n`. It shows the dial Δ (the
    provenance the crunch players asked for) but NOT a 3-row history, the roll-vs-DC column, or
    a distinct actor name.
  - Rationale: chose the pure-UI subset over a client-side history accumulator. The payload
    carries only the single latest impact with no roll/DC/actor/history (see Delivery Finding
    D-Dev above); a local accumulator would have to reconstruct roll-vs-DC by correlating
    `onBeatSelect` + `diceResult` + the next `last_beat_impact` across renders (a `useState`/
    `useEffect` state machine with real re-render-correctness and `key`/deps risk) for a
    same-strip polish story explicitly scoped "pure UI, no protocol change." The honest
    full-fidelity ledger wants the server `beat_history[]` field and belongs to 85-3. This
    matches TEA's deviation above (same conclusion, Dev took the "escalate to 85-3" branch).
  - Severity: minor
  - Forward impact: 85-3 should add `beat_history[]` to the `CONFRONTATION` payload and expand
    `BeatHistoryLedger` to N rows + roll/DC/actor. No 85-1 consumer depends on the missing
    columns; the ledger degrades cleanly (renders what it has).

### Reviewer (audit)
- **TEA deviation (AC5 reduced fidelity)** → ✓ ACCEPTED by Reviewer: sound — the payload genuinely
  lacks the history/roll/DC/actor data; testing only the feedable subset is the honest call.
- **Dev deviation (A5 renders most-recent impact, not 3-row history)** → ✓ ACCEPTED by Reviewer
  (scope only): escalating the full-fidelity ledger to 85-3 is reasonable. **The SCOPE is accepted;
  the IMPLEMENTATION is not** — the single-impact render is wired incorrectly for the opponent side
  (blocking bug in the assessment below). Accepting the deviation does not absolve the bug.
- **UNDOCUMENTED (Reviewer-found):** Dev's commit-row layout change (side-by-side → stacked,
  fixed 200px die lane retired) left the block comment above `<div className="flex flex-col gap-2">`
  still describing the OLD side-by-side "persistent die lane" (Klinger) design. Spec/code drift not
  logged by Dev. Severity: Low (misleading comment, not logic).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; tests 86/86 GREEN; tsc clean; eslint clean | confirmed 0, dismissed 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings (own pass: 1 Low edge — committedBeatId not reset) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings (own pass: no swallowed errors) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 5, downgraded 1 (reduced-motion else = Low) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 2 (stale commit-row, chevron docstring), **dismissed 1** (BeatImpactPanel `opponent.own` — it is CORRECT per 73-7) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings (own pass: `effect:'success'` invalid-union, else types sound) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings (own pass: render-only, no input surface — N/A) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings (own pass: LedgerRow `side`-param design is over-clever — root of the bug) |
| 9 | reviewer-rule-checker | Yes | findings | 5 | confirmed 5 (2× beats?. Rule4, useCallback Rule6, vi.fn Rule8, wiring-test A4) |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 9 confirmed, 1 dismissed (with rationale), 0 deferred

## Reviewer Assessment

**Verdict:** REJECTED

The pipeline was all-green because the defects live in **untested paths**. A clean preflight
means nothing — the most important new feature (A5, the dial-provenance ledger built for the
crunch players) shows the wrong number for the opponent, and the A3 test that should have caught
a floating die never actually exercises its own claim.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [DOC→logic] | `BeatHistoryLedger` "Them" row reads `impact.opponent` (cross-effect, ~0) instead of `impact.own` (the opponent's own dial delta). For `OPPONENT_PRESS{own:2,opponent:0}` it would show **Δ+0**, while `BeatImpactPanel` correctly shows **2**. The A5 ledger exists to give the crunch players legible provenance — showing a wrong delta is an active "lie", the exact failure the OTEL/lie-detector principle guards against. | `ConfrontationOverlay.tsx` `LedgerRow` ~575 | For the Them row read `impact.own ?? 0` (the passed impact IS the opponent's own impact). Simplest: `const delta = impact.own ?? 0` for both rows; `side` labels only. |
| [HIGH] [TEST] | A3 "anchors the roll" test is vacuous — `beat-roll-anchor` renders unconditionally when wired, so the `fireEvent.click` is inert. The AC ("die anchored to the committed beat") is unverified; a detached die would pass. | `spacepass.test.tsx:160` | After click, assert `within(anchor).getByText(/Spot the Contradiction/)` — pin the committed-beat identity to the anchor. |
| [MEDIUM] [TEST] | No test covers the ledger "Them" row — the exact gap that hid the [HIGH] bug. | `spacepass.test.tsx` (A5) | Add an opponent-impact case: `opponent_last_beat_impact{own:2}` → Them row shows `Δ+2`. |
| [MEDIUM] [TYPE/TEST] | `LAST_IMPACT` fixture uses `effect:'success'`, not a member of `BeatEffect` (`advance\|setback\|resolution\|tag\|backfire\|inert`). Renders dead class `beat-impact-success`. Escapes `tsc --noEmit` because the app tsconfig excludes test files (vitest = esbuild, no type-check). | `spacepass.test.tsx:83` | Use `'advance'`. |
| [MEDIUM] [RULE #6] | `handleBeatSelect` is a bare arrow in the render body, passed through `BeatGrid`→`BeatTile`, in a hot game-loop path (GameBoard re-renders per WebSocket msg). GameBoard already `useCallback`-wraps its handler for this reason; the inner layer should match. | `ConfrontationOverlay.tsx:765` | `useCallback((id) => {...}, [onBeatSelect])`. |
| [MEDIUM] [RULE A4] | New suite has no wiring test (all 9 isolation renders). Project rule: every suite needs ≥1 integration test reaching the component from production. (Note: production wiring of the seams IS verified — rule-checker confirmed `BeatHistoryLedger` renders from `ConfrontationOverlay` consumed by `GameBoard.tsx:543` — so this is a TEST-coverage gap, not a wiring break.) | `spacepass.test.tsx` | Add a GameBoard-mount smoke test asserting `confrontation-overlay` renders. |
| [LOW] [RULE #4] | `data.beats?.find` / `data.beats?.length` optional-chain a required `beats: BeatOption[]` field (masks type drift). Mirrors the pre-existing `data.beats ?? []`. | `ConfrontationOverlay.tsx:769,823` | Drop `?.`; or accept as the file's existing defensive pattern. |
| [LOW] [TEST] | Untyped `vi.fn()` for `onDiceThrow` — signature drift in `DiceThrowParams` won't compile-error. | `spacepass.test.tsx:146` | `vi.fn<[DiceThrowParams, number[]], void>()`. |
| [LOW] [DOC] | Stale commit-row comment describes the retired side-by-side "persistent die lane / Klinger" layout; code is now stacked. | `ConfrontationOverlay.tsx` ~809 | Rewrite to the stacked anchored-die intent. |
| [LOW] [TEST] | A1 numeral regex rejects only `9/10px` (no positive size assertion); A5 delta `/\+?2/` is loose; reduced-motion `else` branch is vacuous. | `spacepass.test.tsx:120,212,246` | Add `toMatch(/text-sm\|text-base\|.../)`; tighten to `/Δ\+2/`; broaden the motion query to the overlay scope. |

**Dispatch-tag coverage (all 8 axes):**
- `[TEST]` — A3 vacuous (HIGH), missing Them-row test (MED), invalid fixture effect (MED), untyped `vi.fn` (LOW), loose/narrow regexes + vacuous reduced-motion else (LOW). Confirmed from reviewer-test-analyzer.
- `[DOC]` — stale commit-row comment (LOW, confirmed); chevron docstring (LOW, pre-existing, confirmed); **dismissed** comment-analyzer's `opponent.own` "bug" — it is CORRECT (73-7).
- `[RULE]` — `beats?.` ×2 (Rule 4, LOW), `handleBeatSelect` no `useCallback` (Rule 6, MED), `vi.fn` untyped (Rule 8, LOW), no wiring test (A4, MED). Confirmed from reviewer-rule-checker.
- `[EDGE]` *(subagent disabled — my own pass)* — `committedBeatId` is not reset when `data` switches to a new confrontation; `beats.find` guards it (returns null → no stale caption), so it degrades safely. LOW.
- `[SILENT]` *(disabled — my own pass)* — no swallowed errors; every fallback (`?? 0`, `?? null`, `{cond && ...}`) is an intentional absence signal, not error-masking. No finding.
- `[TYPE]` *(disabled — my own pass)* — `effect:'success'` is an invalid `BeatEffect` (folded into the MED fixture finding); otherwise the new `useState<string|null>`, inline prop types, and unions are sound. No `as any`.
- `[SEC]` *(disabled — my own pass)* — render-only of server-validated `BeatImpactView` data; no user input, no `dangerouslySetInnerHTML`, no injection surface. N/A.
- `[SIMPLE]` *(disabled — my own pass)* — `LedgerRow`'s `side`-param-selects-field design is over-clever and is the *root cause* of the HIGH bug; collapsing to `delta = impact.own ?? 0` for both rows is simpler AND correct.

**Data flow traced (the bug):** `data.opponent_last_beat_impact` → `<BeatHistoryLedger opponent={…}>`
→ `<LedgerRow impact={opponent} side="Them">` → `delta = impact.opponent ?? 0`. For a real
opponent press `{own:2, opponent:0}` this yields `0`, rendered as `Δ+0`, contradicting
`BeatImpactPanel`'s correct `2`. The user-facing number is wrong for the audience the feature
targets. **Unsafe.**

### Rule Compliance

TypeScript lang-review rubric (`.pennyfarthing/gates/lang-review/typescript.md`), enumerated over
the diff (corroborated by reviewer-rule-checker, 47 instances):
- **#1 type-safety escapes:** compliant — no `as any`/`ts-ignore`/non-null assertions (8 instances).
- **#3 enum/union:** compliant — `BeatEffect`/`ConfrontationBranch` are unions, not enums. BUT the
  test fixture assigns a NON-MEMBER (`'success'`) — a values-level violation of the closed union
  (MED finding).
- **#4 null/undefined:** `impact.own ?? 0` / `?? null` correct (0 is valid). `data.beats?.` ×2 →
  VIOLATION (optional chain on required field) — LOW.
- **#6 React/JSX:** `key={beat.id}` stable (compliant); `useState` before early return (compliant,
  hooks order safe); **`handleBeatSelect` lacks `useCallback` in a hot path → VIOLATION (MED)**; no
  `useEffect`, no `dangerouslySetInnerHTML`.
- **#8 test quality:** untyped `vi.fn()` → VIOLATION (LOW); no `as any` in tests (compliant).
- **#2/#5/#7/#9/#10/#11/#12/#13:** compliant or N/A (no async, no JSON.parse, no config/build changes).

SOUL.md / CLAUDE.md:
- **No Silent Fallbacks:** compliant — conditional renders are intentional absence, not masking.
- **No Stubbing:** compliant — `BeatHistoryLedger` renders real data; deferral documented, no empty shell.
- **Verify Wiring (production):** compliant — seams render from `ConfrontationOverlay` → `GameBoard.tsx:543`.
- **Every Test Suite Needs a Wiring Test:** VIOLATION — new suite has none (MED).
- **OTEL / lie-detector spirit:** VIOLATED in effect by the HIGH ledger bug — the player UI asserts a
  mechanical number the engine did not produce. This is precisely the "convincing but wrong" failure
  the principle exists to catch, here in the player-facing surface for Sebastien/Jade.

### Devil's Advocate

Assume this code is broken and hostile to its own users. The flagship deliverable — the A5
beat-history ledger, the one thing this story adds *for* the mechanics-first players who came for
the crunch — lies to them. When the opponent presses and moves their dial +2, the ledger's "Them"
row reads the `opponent` cross-effect field (0) and prints **Δ+0**. Sebastien reads "the engine
says the Queen gained nothing," watches his own dial fall anyway, and concludes the system is
cheating — the exact "reading as unfair" failure Story 73-7 was written to fix, now reintroduced
one panel over. Worse, the BeatImpactPanel two lines up prints the *correct* 2, so the UI
contradicts itself on screen. A confused user can't even tell which number to trust.

Now the safety nets. The A3 test *looks* like it guards the die-anchoring, but it asserts only
that an element exists — an element that exists with or without the click. A future refactor could
detach the die into a corner, reintroduce the very "floating die in a void" L162 complained about,
and this test would stay green. The reduced-motion test has a vacuous `else` that silently
disarms itself if the animation ever moves out of the scoreboard. The fixture seeds an impossible
`effect:'success'` that only survives because the test tsconfig doesn't type-check tests — so the
type system, the thing the union was *designed* to protect, is asleep here.

What would a stressed runtime do? `ConfrontationOverlay` re-renders on every WebSocket frame;
`handleBeatSelect` is reallocated each time and handed to every beat button, defeating the
`useCallback` the GameBoard parent deliberately added — death by a thousand re-renders in the
hottest UI in the app. And `committedBeatId` never resets between confrontations: start a new
duel whose beats happen to reuse an id and the anchor captions the wrong beat. None of this is
hypothetical hand-waving — each is a concrete, reproducible path. The roses are red, and someone
painted them. **Off with this PR's head — back to the Caterpillar.**

**Handoff:** Back to TEA (red rework) — the blocking issues are testable: a failing Them-row
ledger test pins the [HIGH] bug, and the A3 test must be strengthened to assert anchor↔beat
coupling before Dev re-greens.
## TEA Assessment (rework — round 1)

**Tests Required:** Yes (review rework)
**Status:** RED — 16 tests, 15 passing, **1 intended failure** that pins the Reviewer's [HIGH]
ledger bug. Verified via `testing-runner` (RUN_ID 85-1-tea-red-rework). `tsc --noEmit` clean.
Failing test (the bug pin):
- `A5 › shows the OPPONENT's own dial delta in the Them row, not their cross-effect` —
  `Expected element to have text content /Δ\+2/; Received: "Them…Δ0"`. The Them row reads
  `impact.opponent` (0) where it must read `impact.own` (+2). Goes GREEN once Dev fixes `LedgerRow`.

**What I changed (test-side, addressing the Queen's findings):**
- **[HIGH bug pin]** added the failing Them-row ledger test (fixtures `PLAYER_IMPACT own:3` +
  `OPPONENT_IMPACT own:2,opponent:0`); asserts Them row = `Δ+2`, You row = `Δ+3`.
- **[HIGH A3]** rewrote the vacuous A3 test: now asserts the committed beat label is ABSENT from
  the anchor before the click and PRESENT after — the click finally matters.
- **[MED]** fixed the invalid fixture `effect:'success'` → `'advance'` (a real `BeatEffect`).
- **[MED]** added an A5 negative test (no ledger before any impact).
- **[MED]** added the suite wiring test (all five seams via GameBoard's prop surface — see the
  wiring deviation above for why it doesn't mount GameBoard whole).
- **[LOW]** typed the `onDiceThrow` mock (`DiceThrowParams`) instead of bare `vi.fn()`.
- **[LOW]** A1 numeral: added a positive size assertion (`text-sm+`), not just rejecting 9–10px.
- **[LOW]** A5 delta regex tightened `/\+?2/` → `/Δ\+2/`.
- **[LOW]** reduced-motion test de-vacuum'd: asserts `metric-bar-fill` carries the
  `motion-reduce:` guard directly (no self-disarming else branch).

### Dev punch-list (code-side — NOT addressed by tests; the White Rabbit must fix to go GREEN)

1. **[HIGH] `LedgerRow` Them row** (`ConfrontationOverlay.tsx` ~575): read `impact.own ?? 0` for
   the Them row too (the passed impact IS the opponent's own impact). Simplest: `const delta =
   impact.own ?? 0` for both rows; `side` labels only. This greens the failing test.
2. **[MED] `handleBeatSelect` `useCallback`** (~765): wrap `useCallback((id) => {…}, [onBeatSelect])`
   — it's handed to every beat button in a WebSocket-driven hot render path (GameBoard already
   `useCallback`-wraps its handler for this reason). [RULE #6]
3. **[LOW] `data.beats?.` optional chaining** (~769, ~823): `beats` is required (`BeatOption[]`);
   drop the `?.`. [RULE #4] (Or consciously keep the file's pre-existing defensive `?? []` pattern
   and note it — Reviewer's call.)
4. **[LOW] stale commit-row comment** (~809): rewrite the "persistent die lane on the right /
   Side-by-side / Klinger" block to describe the stacked, beat-anchored layout actually shipped.

**Rule Coverage (rework):** the two React-hooks rules flagged "review-time" in round 1 are now
concrete — `key={beat.id}` is stable (compliant); the `useCallback` gap is item #2 above for Dev.

**Handoff:** To Dev (the White Rabbit) for GREEN — fix the punch-list, re-run, push.
## Dev Assessment (rework — round 1)

**Implementation Complete:** Yes
**Status:** GREEN — 93/93 confrontation+dice tests pass (spacepass 16/16 incl. the Them-row pin;
`ConfrontationOverlay.test.tsx` 41/41 incl. the beatless-confrontation regression). `tsc` clean,
`eslint` clean. Verified via `testing-runner` (RUN_ID 85-1-dev-green-rework + re-run).
**Files Changed:** `sidequest-ui/src/components/ConfrontationOverlay.tsx`
**Branch:** feat/85-1-confrontation-panel-legibility (pushed: eda4e55)

**Punch-list disposition (from TEA rework / Reviewer findings):**
1. **[HIGH] LedgerRow Them row** — FIXED. `delta = impact.own ?? 0` for both rows (the passed
   impact is already the acting entity's own `BeatImpactView`). Greens the Them-row pin; matches
   `BeatImpactPanel` + Story 73-7. The over-clever `side`-selects-field design (the [SIMPLE] root
   cause) is gone — `side` is now a label only.
2. **[MED] `handleBeatSelect` useCallback** — FIXED. Wrapped `useCallback((id)=>{…},[onBeatSelect])`,
   hoisted above the `if (!data) return null` early return to keep hook order stable.
3. **[DOC] stale commit-row comment** — FIXED. Rewritten to describe the shipped stacked,
   beat-anchored layout (no more "persistent die lane on the right / Klinger / side-by-side").
4. **[LOW] drop `data.beats?.` optional chaining** — **NOT APPLIED (see deviation below).**

**Handoff:** To Reviewer (the Queen of Hearts) for re-review.

### Delivery Findings — Dev (rework)

- **Conflict** (non-blocking, resolved): the Reviewer/rule-checker [LOW] "drop `data.beats?.`
  optional chaining (beats is required)" is wrong in practice. The existing regression test
  `ConfrontationOverlay.test.tsx › beatless confrontation › renders an empty beat grid …when
  beats is undefined` proves the server CAN broadcast `beats: undefined` despite the
  `BeatOption[]` type. Dropping `?.` crashed it (`TypeError: …reading 'find'`). The optional
  chaining is load-bearing defensive code; restored with an explanatory comment. Affects
  `sidequest-ui/src/components/ConfrontationOverlay.tsx` (and arguably the `ConfrontationData.beats`
  type, which should be `BeatOption[] | undefined` to match the wire — left as-is, out of scope).
  *Found by Dev during implementation (caught by the green-phase regression run).*

### Design Deviations — Dev (rework)

- **Did not apply Reviewer [LOW] finding "drop `data.beats?.` optional chaining"**
  - Spec source: Reviewer assessment [RULE #4] / rule-checker lines 769,823
  - Spec text: "`beats` is required (`BeatOption[]`); the `?.` masks type drift — should be
    `data.beats.find(...)` / `data.beats.length`."
  - Implementation: kept `data.beats?.find(...) ?? null` and `(data.beats?.length ?? 0) > 0`.
  - Rationale: an existing regression test (`beatless confrontation`) pins that the server sends
    `beats: undefined` at runtime; the type is stricter than reality. Removing `?.` reintroduces
    a real production crash. Defensive, not noise.
  - Severity: minor
  - Forward impact: the true fix is to widen `ConfrontationData.beats` to `BeatOption[] | undefined`
    so the type matches the wire — deferred (touches the payload type, out of 85-1 pure-UI scope).
## Subagent Results

_(re-review — round 2, on the full rework diff develop...HEAD)_

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 93/93 GREEN, tsc+eslint clean, 0 smells | confirmed 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | all 5 rework fixes verified SOUND; 5 new = LOW/MED polish, 0 blocking |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 | rework comments all accurate; 1 pre-existing (chevron docstring), non-blocking |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings (render-only — N/A) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings (LedgerRow over-clever design REMOVED in fix) |
| 9 | reviewer-rule-checker | Yes | findings | 1 | hook order/dep array/??/wiring all compliant; 1 LOW type-nit (parentElement cast) |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 0 blocking. Round-1 HIGH×2 both verified RESOLVED. 6 non-blocking LOW/MED polish items captured as delivery findings.

## Reviewer Assessment

_(re-review — round 2)_

**Verdict:** APPROVED

The rework fixed both round-1 HIGH defects, and all four re-review specialists confirm it — no
Critical/High remains. Verified directly:

- **[HIGH→resolved]** `LedgerRow` line 580 now `const delta = impact.own ?? 0` for BOTH rows
  (the over-clever `side`-selects-field design — the [SIMPLE] root cause — is gone). The TEA
  Them-row regression pin is GREEN; mirrors `BeatImpactPanel` + Story 73-7. Data-flow re-traced:
  `opponent_last_beat_impact{own:2}` → Them row → `impact.own` → `Δ+2` (was `Δ+0`). Correct.
- **[HIGH→resolved]** the A3 test now asserts the committed beat label is ABSENT before the
  click and PRESENT after — the click finally carries weight (confirmed by test-analyzer).
- **[MED→resolved]** fixture `effect:'advance'` (valid `BeatEffect`); `vi.fn` typed to
  `(DiceThrowParams, number[])=>void`; wiring test added (substantive — all 5 seams co-render);
  A5 regex tightened to `/Δ\+2/` + negative test; reduced-motion de-vacuum'd (asserts
  `metric-bar-fill` carries `motion-reduce:`); stale commit-row comment rewritten (verified).
- **[MED→resolved]** `handleBeatSelect` wrapped in `useCallback([onBeatSelect])`, hoisted above
  the early return — rule-checker confirms hook order valid and dep array exactly correct.
- **[LOW→correctly declined]** the round-1 "drop `data.beats?.`" finding was NOT applied — an
  existing "beatless confrontation" regression test proves the server sends `beats: undefined`
  at runtime. The optional chain is load-bearing. **Dev's judgment was right; my round-1 finding
  was wrong in practice.** Re-flagging waived (rule-checker concurs).

**Non-blocking findings (captured as delivery findings, not gating):**
- `[RULE]`/`[TYPE]` (LOW) `test:276,281` `.parentElement as HTMLElement` drops `| null` — common
  RTL idiom, structurally non-null, no runtime risk. Cleaner: `data-testid` on ledger rows.
- `[TEST]` (MED) the "200px lane retired" test only checks absence of the inline style — a
  class-based `w-[200px]` reintroduction could slip; add a flex-col structural assertion.
- `[TEST]` (MED) the wiring test asserts seam presence but doesn't fire a beat click to exercise
  `onBeatSelect` — though that chain IS covered by `confrontation-wiring.test.tsx:188,197`
  (verified: clicks a beat, asserts `onBeatSelect` called with the id), so it's polish, not a gap.
- `[TEST]` (LOW) no test for opponent `own: undefined` (the `?? 0` fallback path).
- `[DOC]` (LOW, pre-existing) the `▾ chevron on each tile` docstring describes a feature that
  isn't rendered — predates this story; not introduced by the rework.
- `[EDGE]`/`[SILENT]`/`[SEC]` *(subagents disabled — my own pass)*: `committedBeatId` not reset on
  confrontation change still degrades safely via `beats?.find` → null; no swallowed errors (the
  `??`/conditional renders are intentional absence); render-only, no input/injection surface.

**Rule Compliance (rework):** TypeScript rubric — #1 type-safety (no `as any`/`ts-ignore`; one LOW
test-only `as HTMLElement` cast), #4 null (`??` correct on numeric 0; `beats?.` justified), #6
React (hook order valid, `[onBeatSelect]` dep correct, `key={beat.id}` stable, no `useEffect`
issues), #8 test quality (typed mock, valid fixtures) — all compliant. SOUL/CLAUDE: No Silent
Fallbacks ✓, No Stubbing ✓, Verify Wiring ✓ (seams reachable from `GameBoard.tsx:543`), Every
Test Suite Needs a Wiring Test ✓ (added). OTEL/lie-detector spirit ✓ (the ledger now reports the
true opponent dial delta — the round-1 lie is gone).

### Devil's Advocate

Try to break it. The ledger now reads `impact.own` for both rows — but is the Them row fed the
right object? Traced: `<BeatHistoryLedger impact={last_beat_impact} opponent={opponent_last_beat_impact}>`
→ the Them `LedgerRow` receives `opponent` as its `impact`, so `impact.own` is the opponent's own
delta. Correct, and the regression test pins it. Could `useCallback` go stale? Its dep is
`[onBeatSelect]`; `setCommittedBeatId` is a stable setter — if `onBeatSelect` changes identity
each parent render the callback re-creates, which is correct, not stale. Could the hoisted hooks
break the `data===null` path? Both hooks run before the early return unconditionally — order is
stable across null and non-null renders. Could removing the 200px lane strand the die when no beat
is committed? The anchor renders whenever wired; the caption is gated on `committedBeat`, and
`InlineDiceTray` handles null request/result — no crash. The one residual risk is purely test
brittleness (parentElement scoping, class-based 200px reintroduction) — real-but-LOW, and the
behavior is correct today. I cannot find a correctness, security, or AC defect. The roses are
genuinely red.

**Data flow traced:** opponent dial delta `opponent_last_beat_impact.own` → `LedgerRow impact.own`
→ `Δ+{n}` (Them row). Safe and correct.
**Pattern observed:** hooks hoisted above the early return for stable order — `ConfrontationOverlay.tsx:767-779`.
**Error handling:** `beats?.`/`?? 0`/`?? null` guard the undefined-beats and zero-delta paths; verified by the beatless regression test.
**Handoff:** To SM for finish-story.

### Reviewer (audit — round 2)

- **TEA deviation (wiring test renders ConfrontationOverlay directly, not a mounted GameBoard)**
  → ✓ ACCEPTED by Reviewer: sound — no test in the repo mounts GameBoard (heavy dockview/providers);
  production wiring is verified at `GameBoard.tsx:543`, and the test matches the repo's established
  `confrontation-wiring.test.tsx` idiom. Proportionate.
- **Dev deviation (did not apply Reviewer [LOW] "drop `data.beats?.` optional chaining")**
  → ✓ ACCEPTED by Reviewer: correct call — the "beatless confrontation" regression test proves the
  server sends `beats: undefined`; the optional chain is load-bearing defensive code. My round-1
  finding was wrong in practice. The deferred forward-fix (widen `ConfrontationData.beats` to
  `| undefined`) is the right long-term direction, appropriately out of this story's scope.

### Reviewer (re-review)
- **Improvement** (non-blocking): harden the spacepass suite — `data-testid` on ledger rows
  (replace `parentElement` traversal), a structural flex-col assertion for the retired die lane,
  and an `own: undefined` ledger edge case. Affects
  `sidequest-ui/src/components/__tests__/ConfrontationOverlay.spacepass.test.tsx`. *Found by Reviewer during re-review.*
- **Improvement** (non-blocking, pre-existing): remove/replace the stale `▾ chevron` docstring on
  `ConfrontationOverlay`. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx`. *Found by Reviewer during re-review.*
- **Improvement** (non-blocking): widen `ConfrontationData.beats` to `BeatOption[] | undefined` so
  the type matches the wire (the server can send undefined beats). Affects
  `sidequest-ui/src/components/ConfrontationOverlay.tsx` types. *Found by Reviewer during re-review.*