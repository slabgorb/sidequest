---
story_id: "73-13"
jira_key: null
epic: null
workflow: "tdd"
---
# Story 73-13: BeatImpactPanel render-gate drops opponent readout when player impact absent

## Story Details
- **ID:** 73-13
- **Jira Key:** (no Jira integration)
- **Workflow:** tdd
- **Stack Parent:** none (not stacked)
- **Branch Strategy:** gitflow (feat/73-13-beatimpactpanel-opponent-readout-gate)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T23:30:38Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T00:00:00Z | 2026-06-04T23:15:19Z | 23h 15m |
| red | 2026-06-04T23:15:19Z | 2026-06-04T23:19:39Z | 4m 20s |
| green | 2026-06-04T23:19:39Z | 2026-06-04T23:24:47Z | 5m 8s |
| review | 2026-06-04T23:24:47Z | 2026-06-04T23:30:38Z | 5m 51s |
| finish | 2026-06-04T23:30:38Z | - | - |

## Sm Assessment

**Story:** 73-13 — BeatImpactPanel render-gate drops opponent readout when player impact absent. 2pts, p3, type=bug. Epic 73 (Confrontation Engine Hardening). Workflow: tdd (phased). Repo: sidequest-ui only.

**Why this is well-scoped for tdd:** This is a precise, reviewer-validated UI bug with a known root cause and a known fix. The render gate in ConfrontationOverlay is `{data.last_beat_impact && ...}`, which suppresses the entire BeatImpactPanel whenever the player's own impact is absent — even when an opponent impact is present (opponent-acts-first window: legacy beat_selection path, surprise round, or player taking a non-combat action). That hides the "the enemy hit you" readout that 73-7 added. The reviewer already corrected TEA's earlier "unreachable" claim: `narration_apply.py:4031-4055` preserves opponent-side selections and `last_beat_impacts` accumulates and never clears, so the opponent-present/player-absent state is genuinely reachable. Not a regression, not a crash.

**Expected fix shape (for TEA/Dev, not prescriptive):** gate on `(player_impact || opponent_impact)` and make BeatImpactPanel tolerate an absent player impact (render the opponent readout alone). The fix lives entirely in sidequest-ui — no server change needed.

**TEA's RED target:** a failing component test reproducing the opponent-present / player-absent window where the panel should still render the opponent "hit you" readout but currently renders nothing. Note epic 73 already shipped 73-7/73-8 BeatImpactPanel work and there are existing ConfrontationOverlay/BeatImpactPanel tests to extend rather than start fresh.

**Routing:** RED phase → TEA (Amos Burton).

## TEA Assessment

**Tests Required:** Yes
**Reason:** n/a — reviewer-validated UI render-gate bug with observable DOM behavior; tests are the natural RED.

**Test Files:**
- `sidequest-ui/src/components/__tests__/ConfrontationOverlay.opponentfirstgate.test.tsx` — pins the opponent-acts-first window (player impact absent, opponent present) that 73-7 never covered.

**Tests Written:** 5 tests covering 4 ACs
**Status:** RED (2 failing — the bug; 3 passing — regression guards)

**RED proof (testing-runner, RUN_ID 73-13-tea-red):** File compiles clean (no TS/transform errors).
- AC1+AC2, player impact `undefined` + opponent present → `getByTestId('beat-impact')` throws `Unable to find element [data-testid="beat-impact"]` → **FAIL (bug confirmed)**.
- AC1+AC2, player impact `null` (legacy beat_selection path) + opponent present → **FAIL (bug confirmed)**.
- AC3, neither side present (null/null and undefined/undefined) → panel correctly omitted → **PASS**.
- AC4, both sides present → `beat-impact-own`=3, `beat-impact-opponent`=2, independent → **PASS**.

**Root cause (for Dev/Naomi):** `ConfrontationOverlay.tsx:956` (and the sibling ledger gate at `:965`) gate on `{data.last_beat_impact && ...}` — the PLAYER's impact. The opponent readout (`beat-impact-opponent`) lives *inside* `BeatImpactPanel`, which only receives `impact={data.last_beat_impact}`. When the player half is absent the whole panel — opponent number included — is suppressed.

**Expected GREEN shape (AC-faithful, not prescriptive):** relax the gate to fire on `(data.last_beat_impact || data.opponent_last_beat_impact)`, and make `BeatImpactPanel` tolerate an absent `impact` (its props currently type `impact: BeatImpactView` as required and unconditionally render `impact.summary` / `beat-impact-own`). Render the opponent readout regardless of the player half.

### Rule Coverage

| Rule (sidequest-ui CLAUDE.md) | Test(s) | Status |
|------|---------|--------|
| Every test suite needs a wiring test | All 5 render the production `ConfrontationOverlay` (not `BeatImpactPanel` in isolation) — proves the panel is wired into the overlay render path | covered |
| No silent fallbacks / meaningful assertions | Summaries carry no digit, so number assertions (`'2'`, `'3'`) prove real `own` values, not echoed prose | covered |
| Negative case (test paranoia) | AC3 ×2 assert the panel is *absent* (`queryByTestId(...).not.toBeInTheDocument()`) when no impacts exist — guards against the fix over-rendering an empty shell | covered |

**Rules checked:** 3 of 3 applicable UI-repo rules have test coverage. (OTEL/lang-review backend rules N/A — pure cosmetic-adjacent UI render gate, no server subsystem touched.)
**Self-check:** 0 vacuous tests — every test has ≥1 meaningful assertion; no `let _ =`, no `assert(true)`, no always-None checks.

**Handoff:** To Dev (Naomi Nagata) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/components/ConfrontationOverlay.tsx` — (1) relaxed BOTH render gates (impact panel + history ledger) from `{data.last_beat_impact && ...}` to `{(data.last_beat_impact || data.opponent_last_beat_impact) && ...}`; (2) made `BeatImpactPanel` accept an absent player `impact` — the container (`data-effect`/`data-dial-moved`/className/summary) is now driven by `impact ?? opponent`, and the `beat-impact-own` readout is omitted when the player half is absent; (3) made `BeatHistoryLedger` accept an absent player `impact` — renders the "You" row only when present, "Them" row carries the window alone.
- `sidequest-ui/src/components/__tests__/ConfrontationOverlay.beatimpact.coverage.test.tsx` — updated the 73-9 AC5 test, which explicitly pinned the old (buggy) suppression behavior and named 73-13 as its fix; it now asserts the corrected behavior (panel + opponent readout render, player-own omitted) while keeping its AC5 no-crash intent.

**Resolved TEA's open Question:** chose to **omit** `beat-impact-own` when the player half is absent (rather than render a misleading `0` implying the player acted and whiffed) — symmetric with the existing opponent-omitted path.

**Tests:** 92/92 passing across all 9 ConfrontationOverlay suites (GREEN). The new 73-13 file (5/5) plus the 73-7 opponentbeatimpact and 73-9 coverage suites all green. `tsc --noEmit` clean (the prop-type change from required→optional compiles), `eslint` clean.
**Branch:** feat/73-13-beatimpactpanel-opponent-readout-gate (pushed)

**Handoff:** To next phase (verify or review)

## Delivery Findings

### TEA (test design)
- **Improvement** (non-blocking): The sibling `BeatHistoryLedger` gate at `ConfrontationOverlay.tsx:965` shares the identical `{data.last_beat_impact && ...}` condition, so the beat-history ledger (`data-testid="beat-history-ledger"`) is *also* suppressed in the opponent-acts-first window. The story scope is the impact panel ("enemy hit you" readout), so my tests target `BeatImpactPanel` only — but Dev should fix both gates together since they're one bug with two call sites. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx:965` (relax the ledger gate the same way). *Found by TEA during test design.*
- **Question** (non-blocking): In the player-absent window, should `beat-impact-own` render a misleading `0` (implying the player acted and whiffed), or be omitted symmetric to how the opponent readout is omitted when absent? I left this unasserted to avoid over-constraining the fix; Dev + Reviewer should make the call. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx:746-776` (BeatImpactPanel own-readout rendering when `impact` absent). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The `BeatImpactPanel` container's `data-effect`/styling is now driven by the opponent's beat (`impact ?? opponent`) in the player-absent window. Visually this reads correctly, but a future polish pass could give the THEM-only state its own label/treatment (the existing panel has no "You"/"Them" headers — 73-10 styling territory). Not required by any AC. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx:746-784`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking) [EDGE][TEST]: `BeatHistoryLedger`'s opponent-acts-first behavior has no asserting test. Dev correctly changed the ledger gate + made the "You" row conditional (closing TEA's flagged gap), but the new 73-13 test file asserts only `beat-impact`/`beat-impact-opponent`, never `beat-history-ledger`. The ledger path IS exercised (the AC1+AC2 full-overlay renders would throw if it crashed), so this is a missing *assertion*, not a missing safety net — low risk, but a production change should be pinned. Recommend a fast-follow (or 73-10) adding: AC1/AC2 → `beat-history-ledger` present with only the "Them" row; AC3 → ledger absent. Affects `sidequest-ui/src/components/__tests__/ConfrontationOverlay.opponentfirstgate.test.tsx`. *Found by Reviewer during code review (corroborated by edge-hunter + test-analyzer, high confidence on the gap).*
- **Improvement** (non-blocking) [EDGE]: In the opponent-only window the panel container's `data-effect`/CSS class derives from the OPPONENT's effect (`head = impact ?? opponent`). Verified `beat-impact-advance` → `var(--encounter-player)` (`src/index.css:101`, `src/styles/beat-impact.css:67`), so an opponent "advance" renders the panel in the *player's* encounter color — a valence/attribution mislabel. The mechanical readout (the opponent number, the AC goal) is correct; only the container tint is affected, and the code comment already cedes labels/styling to 73-10. Recommend 73-10 add a `data-actor`/distinct treatment for the opponent-only state. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx:763-774`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking) [SILENT]: `{impact.own ?? 0}` / `{opponent.own ?? 0}` render a missing `own` field as `0`, indistinguishable from a genuine zero-move — which slightly undercuts the mechanics-legibility goal (Sebastien/Jade). PRE-EXISTING (predates 73-13; same pattern in `LedgerRow:617` and the 73-7 spans), so OUT OF SCOPE for this story, noted for a future hardening pass. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx:780,785`. *Found by Reviewer during code review (silent-failure-hunter, medium confidence).*

## Impact Summary

**Upstream Effects:** 2 findings (0 Gap, 0 Conflict, 1 Question, 1 Improvement)
**Blocking:** None

- **Improvement:** The sibling `BeatHistoryLedger` gate at `ConfrontationOverlay.tsx:965` shares the identical `{data.last_beat_impact && ...}` condition, so the beat-history ledger (`data-testid="beat-history-ledger"`) is *also* suppressed in the opponent-acts-first window. The story scope is the impact panel ("enemy hit you" readout), so my tests target `BeatImpactPanel` only — but Dev should fix both gates together since they're one bug with two call sites. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx:965`.
- **Question:** In the player-absent window, should `beat-impact-own` render a misleading `0` (implying the player acted and whiffed), or be omitted symmetric to how the opponent readout is omitted when absent? I left this unasserted to avoid over-constraining the fix; Dev + Reviewer should make the call. Affects `sidequest-ui/src/components/ConfrontationOverlay.tsx:746-776`.

### Downstream Effects

- **`sidequest-ui/src/components`** — 2 findings

### Deviation Justifications

3 deviations

- **Tested against actual two-field payload shape, not the context's nested-field description**
  - Rationale: Story scope > context approximation (spec-authority hierarchy). The context captured the *intent* (render when either side has an impact) correctly but named fields that don't exist; testing the real shape keeps the RED honest and the Dev unblocked.
  - Severity: minor
  - Forward impact: none — AC intent unchanged; only the field path the Dev edits differs.
- **Modified a pre-existing sibling test (73-9 AC5) that pinned the old behavior**
  - Rationale: 73-13 is the named story that flips this behavior; the test characterized a bug, not a contract. Leaving it would have failed CI and pinned the very bug 73-13 fixes. Story scope outranks a lower-authority characterization test (spec-authority hierarchy).
  - Severity: minor
  - Forward impact: none — the 73-9 characterization now reflects shipped behavior; the AC6 inert-summary tests in the same file are untouched.
- **Resolved TEA's open Question by omitting the player-own readout (not rendering 0) when the player half is absent**
  - Rationale: A `0` would imply the player acted and moved nothing (false in the opponent-acts-first window). Omission matches the established per-side rendering convention and is not contradicted by any AC.
  - Severity: minor
  - Forward impact: none — no test or sibling story asserts a player-own readout in the player-absent window.

## Design Deviations

### TEA (test design)
- **Tested against actual two-field payload shape, not the context's nested-field description**
  - Spec source: context-story-73-13.md, "Solution" §1
  - Spec text: "Relax the render gate to `(data.last_beat_impact && (data.last_beat_impact.player_impact || data.last_beat_impact.opponent_impact))`"
  - Implementation: The live payload has NO nested `player_impact`/`opponent_impact` — it carries two sibling top-level fields, `last_beat_impact` (player) and `opponent_last_beat_impact` (opponent), each a `BeatImpactView` (see `ConfrontationOverlay.tsx:166,171`). Tests drive those real fields; the AC-faithful gate is `(data.last_beat_impact || data.opponent_last_beat_impact)`.
  - Rationale: Story scope > context approximation (spec-authority hierarchy). The context captured the *intent* (render when either side has an impact) correctly but named fields that don't exist; testing the real shape keeps the RED honest and the Dev unblocked.
  - Severity: minor
  - Forward impact: none — AC intent unchanged; only the field path the Dev edits differs.

### Dev (implementation)
- **Modified a pre-existing sibling test (73-9 AC5) that pinned the old behavior**
  - Spec source: 73-13 story scope (session) + context-story-73-13.md AC1/AC2; conflicting test `ConfrontationOverlay.beatimpact.coverage.test.tsx:59-77`
  - Spec text: 73-9 test asserted "Panel gated off → no player section, no opponent section" when `last_beat_impact: null` with a valid opponent impact — explicitly labeled "the 73-13 bug (a production change, out of scope for this test-only story). This pins what ships TODAY."
  - Implementation: Inverted the test's three assertions to the corrected 73-13 behavior (panel present, `beat-impact-opponent` shows the opponent number, `beat-impact-own` omitted), preserving its original AC5 no-crash intent.
  - Rationale: 73-13 is the named story that flips this behavior; the test characterized a bug, not a contract. Leaving it would have failed CI and pinned the very bug 73-13 fixes. Story scope outranks a lower-authority characterization test (spec-authority hierarchy).
  - Severity: minor
  - Forward impact: none — the 73-9 characterization now reflects shipped behavior; the AC6 inert-summary tests in the same file are untouched.
- **Resolved TEA's open Question by omitting the player-own readout (not rendering 0) when the player half is absent**
  - Spec source: Delivery Findings → TEA (test design), the `beat-impact-own` Question
  - Spec text: "should `beat-impact-own` render a misleading `0` ... or be omitted symmetric to how the opponent readout is omitted when absent?"
  - Implementation: Gated `beat-impact-own` on `impact != null`, so it is omitted in the player-absent window — symmetric with the existing `opponent != null` gate on the opponent readout.
  - Rationale: A `0` would imply the player acted and moved nothing (false in the opponent-acts-first window). Omission matches the established per-side rendering convention and is not contradicted by any AC.
  - Severity: minor
  - Forward impact: none — no test or sibling story asserts a player-own readout in the player-absent window.

### Reviewer (audit)
- **TEA — Tested against actual two-field payload shape** → ✓ ACCEPTED by Reviewer: the live payload genuinely carries two sibling fields (`last_beat_impact` / `opponent_last_beat_impact`, `ConfrontationOverlay.tsx:166,171`); the context's nested-field text was an approximation. Testing the real shape is correct and the AC intent is preserved.
- **Dev — Modified the pre-existing 73-9 AC5 test** → ✓ ACCEPTED by Reviewer: the original test self-documented that it pinned "the 73-13 bug ... what ships TODAY" — it characterized a bug, not a contract, and 73-13 is the named story that flips it. The update preserves the AC5 no-crash intent and strengthens it with a real `toHaveTextContent('2')` assertion (confirmed by test-analyzer). Leaving it would have pinned the very bug being fixed.
- **Dev — Omitted the player-own readout (not `0`) when the player half is absent** → ✓ ACCEPTED by Reviewer: sound UX call, symmetric with the existing `opponent != null` gate, contradicted by no AC. A `0` would have falsely implied the player acted and whiffed.
- No undocumented deviations found. The two `?? 0` masking patterns and the opponent-effect container styling are pre-existing or 73-10-scoped, captured as non-blocking Delivery Findings rather than deviations from this story's spec.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (92/92 green, tsc+eslint clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 8 | confirmed 2 (non-blocking), dismissed 4 (correct paths / pre-existing), deferred 2 (extra test variants) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 1 as non-blocking pre-existing (`?? 0`), dismissed 2 (by-design `head` fallback + duplicate `?? 0`) |
| 4 | reviewer-test-analyzer | Yes | findings | 3 | confirmed 1 (ledger test gap, non-blocking), deferred 2 (data-effect + undefined/undefined ledger assertion) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 | dismissed 1 (low, forward-looking dangerouslySetInnerHTML caution; no present vuln, no perception leak) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 2 confirmed (both non-blocking, Medium), 7 dismissed (with rationale), 4 deferred (extra test coverage for a fast-follow)

## Reviewer Assessment

**Verdict:** APPROVED

A tight, correct 2-point UI render-gate fix. The opponent-acts-first window (player impact absent, opponent present — an accumulating, reviewer-confirmed-reachable state) used to suppress the entire BeatImpactPanel, hiding the opponent "hit you" readout 73-7 added. Both render gates and both panels now fire on `(player || opponent)` and tolerate an absent player impact. 92/92 tests green across 9 ConfrontationOverlay suites; `tsc --noEmit` and `eslint` clean; zero code smells.

**Observations (≥5):**
- [VERIFIED] Gate/panel consistency — evidence: gates at `ConfrontationOverlay.tsx:970,983` use `(a || b)`; `BeatImpactPanel:763` self-guards with `head = impact ?? opponent; if (!head) return null`. No `(impact,opponent)` combination passes the gate then renders an empty shell. Complies with "No Silent Fallbacks" (explicit early return, not a masked default).
- [VERIFIED] No crash on any null path — evidence: `LedgerRow` is guarded by `{impact && <LedgerRow .../>}` (`:652`) so it never receives null; `BeatHistoryLedger:646` early-returns when both absent. The full 9×... truth table was traced; no read off `head` can hit undefined.
- [VERIFIED] Both-present case unchanged — evidence: `head = impact ?? opponent` resolves to `impact` when present (`:763`), so `data-effect`/summary/`beat-impact-own` are identical to pre-73-13 behavior; the 73-7 opponentbeatimpact suite (own=3, opponent=2) stays green.
- [EDGE][TEST] [MEDIUM] BeatHistoryLedger opponent-first behavior is unasserted — the ledger gate + "You"-row change ship without a `beat-history-ledger` assertion in the new file. Implicitly smoke-covered (renders without throwing), low-risk, non-blocking. Captured as a Delivery Finding for a fast-follow.
- [EDGE] [MEDIUM] Opponent-only container valence — `beat-impact-${head.effect}` derives from the opponent in that window; verified `beat-impact-advance` → `--encounter-player` (`index.css:101`), so the panel tints in the player's color when the enemy acted. Cosmetic attribution only; the mechanical number is correct; 73-10 owns styling. Non-blocking.
- [SILENT] [LOW] `{impact.own ?? 0}` / `{opponent.own ?? 0}` mask a missing `own` as `0` — PRE-EXISTING (predates this diff; also in `LedgerRow:617`), out of scope, noted for future hardening.
- [SEC] [LOW] No present vulnerability — `head.summary` renders as escaped React text (no XSS); `opponent_last_beat_impact` was already on this client's payload and already rendered when the player also had an impact, so widening the gate changes *when* it renders, not *whether* the data reaches the client — no ADR-104/105 perception-firewall leak. Forward-looking note only: never route `summary` through `dangerouslySetInnerHTML` without sanitizing.
- [DOC] N/A — comment_analyzer disabled via settings. (Diff comments self-checked: the three new comments accurately describe the gate change and cite 73-13/73-10; no stale/misleading docs.)
- [TYPE] N/A — type_design disabled via settings. (Self-checked: prop type relaxed `BeatImpactView` → `BeatImpactView | null | undefined` on two internal components; tsc clean; callers already pass nullable `data.last_beat_impact`.)
- [SIMPLE] N/A — simplifier disabled via settings. (Self-checked: change is minimal — gate widening + two early-return guards; no dead code or over-engineering introduced.)
- [RULE] N/A — rule_checker disabled via settings. (Self-checked against project rules below.)

**Rule Compliance:**
- *No Silent Fallbacks* — `head = impact ?? opponent` and the two early-return guards are explicit optional-render handling for an expected (documented) state, not a masked config/path default. COMPLIANT. (The pre-existing `?? 0` spans are flagged separately as out-of-scope.)
- *No Stubbing* — no stubs/placeholders introduced. COMPLIANT.
- *Wire Up What Exists / Verify Wiring* — change lives in the production `ConfrontationOverlay` render path; the new tests render the production component (not the panel in isolation), and `src/__tests__/confrontation-wiring.test.tsx` already pins App→GameBoard→Overlay wiring. COMPLIANT.
- *Every Test Suite Needs a Wiring Test* — satisfied: all 5 new tests exercise the production overlay end-to-end. COMPLIANT (with the noted non-blocking ledger-assertion gap).
- *OTEL on subsystem fixes* — sidequest-ui CLAUDE.md explicitly exempts "cosmetic UI changes." This is a pure render-gate visibility change with no engine/subsystem decision; no OTEL required. COMPLIANT.

**Data flow traced:** server `CONFRONTATION` payload → `data.opponent_last_beat_impact` → gate `(last_beat_impact || opponent_last_beat_impact)` → `BeatImpactPanel`/`BeatHistoryLedger` → `beat-impact-opponent` span renders `opponent.own` as escaped text. Safe — no untrusted-input execution, no withheld data surfaced.

**Pattern observed:** clean optional-render with explicit early-return guards and per-side conditional spans — consistent with the existing `{opponent != null && ...}` convention at `ConfrontationOverlay.tsx:769`.

**Error handling:** all-absent → both panels return null (guarded at gate and internally); missing `own` → `?? 0` (pre-existing, non-blocking).

### Devil's Advocate

Argue this is broken. The most damning angle: the panel now lies about who acted. In the opponent-acts-first window the container's `data-effect`, `data-dial-moved`, and summary text are all sourced from the *opponent's* BeatImpactView, yet the panel has no actor label — a player glancing at it sees "Hamish presses the advantage" rendered in `--encounter-player` (their own success color) and could read it as something *they* did well. A confused, fast-reading player (Alex under time pressure) misattributes a hit-against-them as a win-for-them. That is a genuine legibility regression versus a properly-labeled readout — but it is strictly better than the pre-fix state (nothing rendered at all), and the authoritative mechanical number is correct and correctly attributed via the `beat-impact-opponent` testid. A malicious server could send `opponent_last_beat_impact` with a 10,000-char `summary` or a bogus `effect` string; the former just overflows a flex span (CSS clips/wraps, no crash), the latter yields an unknown `beat-impact-${effect}` class that simply goes unstyled — neither is exploitable, and React escapes the text so no injection lands. A stressed payload that omits `own` shows `0` — misleading but pre-existing and non-fatal. The untested ledger could, in theory, regress to an empty shell if a *future* edit diverges its internal guard from the outer gate; today it cannot, because both gate and guard agree. None of these rise to data corruption or a crash. The valence mislabel is real and worth a 73-10 follow-up, but it is cosmetic, non-regressive, and explicitly out of this story's scope. Verdict stands: APPROVED with documented non-blocking follow-ups.

**Handoff:** To SM for finish-story