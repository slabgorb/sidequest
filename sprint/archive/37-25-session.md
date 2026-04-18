---
story_id: "37-25"
jira_key: ""
epic: "37"
workflow: "trivial"
---

# Story 37-25: Target number shown before the roll

## Story Details

- **ID:** 37-25
- **Title:** Target number shown before the roll — display DC/mod/need on ability click, persist through dice animation, resolve color against known target, make consistent across all abilities
- **Jira Key:** (none — personal project)
- **Workflow:** trivial
- **Repos:** ui
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-18T22:32:17Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-18T17:00:00Z | 2026-04-18T21:00:07Z | 4h |
| implement | 2026-04-18T21:00:07Z | 2026-04-18T22:29:03Z | 1h 28m |
| review | 2026-04-18T22:29:03Z | 2026-04-18T22:32:17Z | 3m 14s |
| finish | 2026-04-18T22:32:17Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- **Question** (non-blocking): `lastRequestIdRef.current` is updated synchronously before the 100ms timer in `sidequest-ui/src/dice/InlineDiceTray.tsx` auto-roll useEffect — a pre-existing pattern, not introduced by 37-25. If `isRollingPlayer` ever flips from false→true after the ref is consumed but before the timer fires, the same request_id can't re-trigger a roll. Affects `sidequest-ui/src/dice/InlineDiceTray.tsx` (consider moving ref assignment into the timer callback in a future story if this becomes observable). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `noopThrow` in `sidequest-ui/src/dice/InlineDiceTray.tsx:236` silently swallows any future `PickupDie` throw events (pre-existing). Affects `sidequest-ui/src/dice/InlineDiceTray.tsx` (replace with an invariant-violation throw if `PickupDie` is ever re-enabled). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- Dev logged no deviations. Reviewer concurs — implementation matches the spec Bossmang gave Dev (risk-colored buttons, 100ms pre-roll pause) and the SM assessment (target shown on click, persists through animation, color against known target).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-ui/src/components/ConfrontationOverlay.tsx` — added `riskColor()` helper and applied HSL green→red gradient (borderColor + color) to beat action buttons based on `|metric_delta|`. Kept `font-bold` for resolution beats; dropped the destructive override so the gradient is authoritative. Added `data-risk` attribute for debug/testing visibility.
- `sidequest-ui/src/dice/InlineDiceTray.tsx` — wrapped the auto-roll useEffect in a 100 ms `setTimeout` so the "DC · mod · need" readout registers with the player before the physics starts. Cleanup returns `clearTimeout` to prevent stale rolls on rapid request changes or spectator transitions.

**Tests:** ConfrontationOverlay.test.tsx 35/35 GREEN. Runner reports 29 pre-existing failures in 4 unrelated files (Three.js/useLoader mocks in dice rendering tests) — not touched by this change.

**Branch:** `feat/37-25-target-number-shown-before-roll` (pushed)

**Per Bossmang's spec:**
- Risk-colored buttons (green = safe → red = risky) using `|metric_delta|` ÷ 10 clamped to [0,1], mapped to HSL hue 120→0. Exact DC stays hidden — players see qualitative risk, read the precise "need N" only after committing.
- "need N" appears the instant `diceRequest` is set (same frame as click); 100 ms pause inserted before physics so the number is readable rather than blurred past.
- DC/mod/need line in `InlineDiceTray` already persists through the animation and until the 3 s post-result auto-dismiss — no change needed there.

**Handoff:** To Chrisjen Avasarala (Reviewer).

## Sm Assessment

Trivial 2pt UI-only story. Scope: when a player clicks an ability, display the target number (DC + modifier = need) before the dice roll, keep it visible through the dice animation, and color-resolve the result against that target consistently across all abilities.

**Repos:** ui only. No API or content changes.

**Technical approach (Dev to verify):**
- Find the ability-click → dice-request handoff in the UI (likely a dice/ability overlay component).
- Ensure the target number (DC, modifier, final need) is part of the dice request payload or locally computable at click time, and rendered in the pre-roll UI.
- Persist that display through the dice animation lifecycle (don't clear on roll start).
- Use the known target to resolve success/fail coloring uniformly — no per-ability one-offs.

**Acceptance:**
- Target shown on click for every ability, not just some.
- Target persists during dice animation.
- Result color matches the displayed target.

**Non-goals:** Changing DC formulas, protocol changes, new ability types.

Handoff to Naomi Nagata (Dev).
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Skipped | disabled | N/A | Skipped — 35-line cosmetic UI diff, existing ConfrontationOverlay.test.tsx 35/35 green verified manually (npx vitest run) |
| 2 | reviewer-edge-hunter | Yes | findings | 3 | confirmed 0, dismissed 2, deferred 1 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | confirmed 0, dismissed 2 (both pre-existing, out of diff scope — logged as delivery findings) |
| 4 | reviewer-test-analyzer | Yes | findings | 1 | dismissed 1 |
| 5 | reviewer-comment-analyzer | Skipped | not applicable | N/A | Skipped — diff is 35 lines, comments added are clear (story ref + rationale) |
| 6 | reviewer-type-design | Skipped | not applicable | N/A | Skipped — no new types, no API surface, no newtype/enum opportunities |
| 7 | reviewer-security | Skipped | not applicable | N/A | Skipped — cosmetic UI change, no auth/data/tenant surface |
| 8 | reviewer-simplifier | Yes | findings | 3 | dismissed 3 (all low/medium — see rationale below) |
| 9 | reviewer-rule-checker | Skipped | not applicable | N/A | Skipped — no lang-review rules apply to inline HSL strings and setTimeout wrappers in a cosmetic React component |

**All received:** Yes (4 spawned, 4 returned; 5 skipped with rationale for a 2pt trivial cosmetic UI diff)
**Total findings:** 0 confirmed, 8 dismissed (with rationale), 1 deferred to Delivery Findings

### Finding Dispositions

- **[EDGE] riskColor with NaN/Infinity** — Dismissed. `metric_delta` originates from server-validated `BeatOption` (integer field in YAML); non-finite values would indicate a deeper data-layer bug that this defensive branch would only paper over. No silent fallback desired per CLAUDE.md.
- **[EDGE] lastRequestIdRef updated before setTimeout** — Deferred as Delivery Finding (Question/non-blocking). Pre-existing pattern, not introduced by 37-25. No evidence `isRollingPlayer` flips mid-request in practice.
- **[EDGE] setTimeout race with new diceRequest mid-window** — Dismissed. `setDiceRequest` always produces a new payload object; React re-runs the effect with new identity, triggering cleanup before the new scheduling. Verified by reading the effect's dependency array.
- **[SILENT] `needed = 0` fallback** — Dismissed. Pre-existing, rendered only inside `{diceRequest && ...}`. Captured as reviewer note; no behavior change in this story.
- **[SILENT] noopThrow stub** — Dismissed for this PR, captured as Delivery Finding (Improvement/non-blocking). Pre-existing; PickupDie is not reachable from the auto-roll path.
- **[TEST] Unit test for riskColor** — Dismissed with rationale. `riskColor` is a 4-line pure function; its output shapes button style rendered by ConfrontationOverlay, which is already exercised by 35 passing integration tests. A dedicated unit test is over-coverage for a 2pt trivial cosmetic story; no project rule mandates unit coverage per pure helper. Re-evaluate if `riskColor` ever takes on conditional branching.
- **[SIMPLE] riskColor single call site** — Dismissed. Extracting the helper improves testability (per the test-analyzer finding above — the two are in tension) and keeps the button JSX scannable.
- **[SIMPLE] data-risk attribute has no consumer** — Dismissed. Cheap debug aid; useful for GM-panel inspection, future E2E selectors, and visual-regression diffs. No performance or correctness cost.
- **[SIMPLE] Drop setTimeout cleanup return** — Dismissed. React best practice is to always clean up timers from effects; the 100ms window is short but the cleanup prevents stale roll triggers on rapid re-clicks (edge-hunter's race scenario).

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Beat button click → `handleBeatSelect` (App.tsx:558) → `setDiceRequest(localReq)` → `InlineDiceTray` useEffect (100 ms delay) → `DiceScene` auto-roll → `onThrow` → server `DICE_THROW`. Pre-roll target line (`DC X · STAT ±Y · need Z`) shown from the click frame; persists until 3 s after `DICE_RESULT`. Safe — no protocol changes, no new server messages, server `outcome` still drives result coloring.

**Pattern observed:** HSL green→red risk gradient at `sidequest-ui/src/components/ConfrontationOverlay.tsx:149-156` (`riskColor` helper) is a clean, idiomatic mapping — matches the CLAUDE.md "no magic literals, explain your math" bar and commits to showing qualitative risk only (not the exact DC), respecting Keith's "tension through ignorance" directive.

**Pre-roll pause:** 100 ms `setTimeout` in `sidequest-ui/src/dice/InlineDiceTray.tsx:193-205` with correct cleanup — short enough to feel snappy, long enough for the eye to register the "need N" line before physics kick in. Serves Sebastien (mechanical-first player) and Alex (needs pacing).

**Error handling:** No new error surfaces. `riskColor` operates on a trusted server-validated integer; useEffect cleanup guards against stale timer firing on unmount or rapid re-clicks.

**Security:** N/A — cosmetic render-layer change.

**Wiring check:** `riskColor` is called at `ConfrontationOverlay.tsx:171`; `BeatActions` is the only renderer of beat buttons and is mounted in `ConfrontationOverlay` (`GameBoard → ConfrontationOverlay`). `InlineDiceTray` is mounted from `ConfrontationOverlay` when `diceRequest` is active. End-to-end reachable.

### Devil's Advocate

What could go wrong? A malicious or malformed genre pack could ship a beat with `metric_delta: 10000`, producing `risk = 1`, pure red — fine, clamp holds. A pack shipping `metric_delta: -5` produces the same color as `+5` — fine and intentional, since the DC formula uses `Math.abs`. A pack shipping `metric_delta: null` (schema violation) would produce `Math.abs(null) = 0` → green — arguably wrong, but that's a content-validation failure upstream, not a UI concern. A pack shipping NaN via a bug in the YAML loader produces `hsl(NaN, 60%, 50%)` which browsers drop, leaving the button with default foreground color — degraded but not broken; the button still renders, still clickable, still labelled. A confused user sees a yellow-ish "Ram" and a near-red "Break the Line" and chooses Ram expecting safety — and it still might fail on the roll; that's the tension Keith wants. A stressed renderer: the transition-colors CSS class combined with inline style swap creates a brief transition frame on color changes, but beats don't mutate in place during an active confrontation (confrontation swap clears and remounts). A spectator seeing the colors during another player's turn: same color palette shown, no private info leaked. The 100 ms pause on a slow connection: timer is client-side, independent of network — pause is deterministic. On a flaky/paused JS thread (dev tools open, heavy GC): setTimeout fires later than 100 ms, acceptable. On component unmount before the timer: cleanup cancels it — the pending roll is lost but the dice tray is gone anyway. I cannot find a scenario where this change introduces new correctness risk.

**Specialist coverage (tagged):**
- [EDGE] 3 findings — 1 deferred to delivery findings (pre-existing ref-update pattern), 2 dismissed (NaN defensive guard not warranted; React identity-change handles the mid-window race).
- [SILENT] 2 findings — both pre-existing (`needed = 0` inside guarded block, `noopThrow` unreachable stub); captured in delivery findings, not in this diff.
- [TEST] 1 finding — dismissed; `riskColor` is a 4-line pure function whose output is exercised by 35 passing integration tests in `ConfrontationOverlay.test.tsx`.
- [SIMPLE] 3 findings — all dismissed; helper extraction supports testability, `data-risk` is a cheap debug selector, cleanup return is idiomatic React.
- [DOC] Not spawned — two added comments (story ref + rationale) are clear and current; no stale docs in diff.
- [TYPE] Not spawned — no new types, enums, traits, or API surface. `riskColor` takes `number` and returns `string`; no newtype opportunity.
- [SEC] Not spawned — cosmetic render change, no auth/tenant/data-flow surface.
- [RULE] Not spawned — no Rust/Python rules apply; TypeScript diff introduces no patterns on which project rules speak.

**Delivery findings captured:** 2 (one pre-existing pattern question, one pre-existing stub improvement). Neither blocks merge.

**Handoff:** To Camina Drummer (SM) for finish-story.