---
story_id: "69-2"
jira_key: null
epic: "69"
workflow: "tdd"
---
# Story 69-2: Opening gameboard — full-width action input under narrative + co-located high-contrast HP pip scale

## Story Details
- **ID:** 69-2
- **Epic:** 69 (Gameboard & dice UX polish)
- **Jira Key:** (none — story not yet synced to Jira)
- **Type:** Bug (UX)
- **Points:** 3
- **Priority:** P2
- **Repos:** sidequest-ui
- **Workflow:** TDD (Red → Green → Spec-Check → Verify → Review → Spec-Reconcile → Finish)

## Context

This story implements a key playtest-3 finding (ADR-036 amendment 2026-05-03, CLAUDE.md player-audience section): the action input field is currently positioned in a way that may rush slow typists (Alex) and doesn't surface mechanical feedback legibly for mechanics-first players (Sebastien, Jade).

**Source:** sq-playtest-pingpong.md, Epic 69 description

**Audience Impact:**
- **Alex (slow typist):** Full-width input bar under narrative, with visible submit-and-wait turn barrier, gives her time to type without feeling rushed by fast typists.
- **Sebastien & Jade (mechanics-first):** High-contrast HP pip scale co-located with action input makes mechanical state visible during player action submission — they can see the numbers backing the narration.

## Technical Approach

### Current State
The GameBoard component (React/TypeScript, sidequest-ui) currently positions the action input within PartyPanel or a sidebar location. Player UI must expose:
1. Narrative cards at top
2. Full-width action input bar beneath narrative
3. High-contrast HP pip scale co-located with action input (adjacent or inline)

### Acceptance Criteria

1. **Layout AC-1:** Action input bar is full-width below the narrative area (not sidebar, not collapsed)
   - Visible from game start (opening gameboard / character creation exit flow)
   - Submit button and text input in a horizontal row
   - Clear visual hierarchy: narration → input → HP state

2. **Layout AC-2:** HP pip scale is co-located and high-contrast
   - Renders party HP as a visual pip/dot scale per character
   - High contrast (dark bg, bright pips) for visibility during live narration
   - Updates reactively when HP changes (no page refresh required)
   - Positioned adjacent to or inline with the action input (same container or grouped row)

3. **Responsive AC-3:** Input bar and HP scale remain usable on smaller viewports
   - Mobile: full-width input still accessible (no horizontal scroll to reach it)
   - Tablet: pips stack or inline depending on party size (no overflow)
   - Desktop: pips inline, horizontal layout

4. **Mechanical Legibility AC-4:** Numbers are visible and match server state
   - Each character pip label or tooltip shows `current_hp / max_hp` or a clear damage indicator
   - Player-facing UI reflects true game state (UI-reactivity assertion, NOT an OTEL/telemetry requirement)
   - Dice resolution + HP changes propagate reactively through WebSocket (ADR-026, ADR-027)

5. **Integration AC-5:** Action input submit → state mirror update → HP reflect
   - Submit action via WebSocket (existing handler path)
   - Server updates HP (if applicable)
   - Client state mirror reflects change (useStateMirror hook, ADR-026)
   - HP pips re-render without manual refresh

### Component Changes (likely touch-points)

**Primary:**
- `GameBoard.tsx` — main layout container; tag the input wrapper `gameboard-input-region` (`w-full`) in BOTH the mobile (MobileTabView, ~line 732) and desktop (input-area, ~line 800) layouts; render the new HP scale inside the shared `inputBar` block (~line 534-571) so it co-locates in both layouts.
- `HpPipScale.tsx` (NEW) — extracted, reusable co-located HP pip component. Reuse the `EdgeBadge`/`FolioEdgeTicks` idiom (currently module-private in CharacterPanel.tsx) rather than inventing a new health widget.
- `CharacterPanel.tsx` — source of the pip idiom (`FOLIO` token map, ♦ diamond pips, ≤25% danger threshold). Consider extracting `EdgeBadge`/`FolioEdgeTicks` so both CharacterPanel and HpPipScale share one implementation.

**Secondary (test wiring):**
- HP flows `PARTY_STATUS` → `useStateMirror` → `GameStateProvider` → `GameBoard.characters` prop. No server/protocol change.

## Sm Assessment

UI-only story, cleanly scoped to sidequest-ui. Selected by Keith directly as a deliberately UI-only pick. Two distinct deliverables, both traceable to playtest-3 audience findings:

1. **Full-width action input under narrative** — serves Alex (slow typist): generous, unmissable input target beneath the narration, reinforcing the submit-and-wait pacing doctrine (ADR-036). Do not let this regress peer-action visibility during the wait phase.
2. **Co-located high-contrast HP pip scale** — serves Sebastien/Jade (mechanics-first): HP legible in the **player-facing** surface. Note this is a player-UI concern, NOT a dev/OTEL/GM-panel concern — keep the framing on what the player sees, not backend observability.

No Jira key (story unsynced); Jira claim correctly skipped. Workflow is tdd/phased → next owner is TEA for RED. AC-4/AC-5 reference server-state/OTEL verification — that's a GREEN-phase wiring check, not a request to build dev observability into the player UI. TEA should write failing tests against the layout + reactive HP-pip behavior, including the mandatory wiring test (HPScale imported and consumed by GameBoard in production).

Handing off to RED.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Player-facing UI behavior with concrete layout + reactive-state ACs; not a chore.

**Test Files:**
- `src/__tests__/hp-pip-scale-component-69-2.test.tsx` — focused behavioral contract for the new reusable `HpPipScale` component (pip count, fill, accessible `HP cur of max` label, ≤25% danger threshold, 0/full edge cases, local-player resolution, empty-party safety). 9 cases.
- `src/__tests__/opening-gameboard-input-region-69-2.test.tsx` — GameBoard WIRING (does not import the new component, so it loads/runs today): full-width `gameboard-input-region` containing both `input-bar` and `input-hp-scale`, DOM ordering after narrative, reactive HP update on `characters[]` change, and presence across mobile + desktop layouts. 6 cases.

**Tests Written:** 15 tests covering 5 ACs.
**Status:** RED (failing — ready for Dev). Confirmed via testing-runner (RUN_ID 69-2-tea-red-2):
- Component file: suite fails to resolve `@/components/HpPipScale` (component absent) — acceptable RED.
- Wiring file: 6 tests ran and failed cleanly on missing `[data-testid="gameboard-input-region"]`; harness HEALTHY (GameBoard renders, no provider/import crash). Good RED, no vacuous passes.

### Why the split (RED quality)
Initial single file failed at vite transform time on the unresolved dynamic import, blocking all 18 tests from executing (0 ran). That masked whether the GameBoard wiring harness was itself sound. Splitting isolates the not-yet-existing component (import-fail RED) from the wiring tests (which now load, run, and fail on the real missing-element assertion) — proving the harness is correct before Dev starts.

### Rule Coverage (TypeScript lang-review checklist)

| Rule | How addressed in test design | Status |
|------|------------------------------|--------|
| #4 null/undefined (`??` vs `||`, falsy 0) | `hp: 0` edge-case test asserts 0 HP renders all-empty + danger (0 must not be treated as "missing"); empty-party test asserts no crash | failing (RED) |
| #6 React/JSX (`key={index}`, hooks deps) | Note for Dev: the reused `FolioEdgeTicks` uses `key={index}` on static pips — acceptable (pips never reorder); do NOT copy `key={index}` onto any reorderable list | advisory |
| #8 test quality (no `as any`, meaningful asserts) | Every test asserts a concrete value (pip counts, exact aria-label string, danger class presence/absence); no `as any`; no vacuous `is*` checks | self-checked clean |
| #10 input validation | Component is presentational (consumes typed `CharacterSummary`); no user-input parsing in scope | n/a |
| Wiring (project rule: every suite needs a wiring test) | `opening-gameboard-input-region-69-2.test.tsx` asserts `input-hp-scale` is rendered inside GameBoard's production `gameboard-input-region` — non-test consumer | failing (RED) |

**Rules checked:** 5 of the applicable lang-review/project rules have test coverage or explicit advisory.
**Self-check:** 0 vacuous tests found. testing-runner confirmed no File-B test unexpectedly passed.

**Handoff:** To Dev for implementation.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `src/components/HpPipScale.tsx` (NEW) — co-located high-contrast HP pip scale. Resolves the local player by `currentPlayerId` (fallback first character), renders `HP cur/max` label + one pip per max-HP unit (`data-testid="hp-pip"`, `data-filled`), destructive tone at ≤25%, ADR-079 theme tokens (`--primary`, `--border`, `destructive`). Container `data-testid="input-hp-scale"`, group `data-testid="hp-pip-group-{player_id}"` with `aria-label="HP {cur} of {max}"`.
- `src/components/GameBoard/GameBoard.tsx` — imported `HpPipScale`; tagged the shared `inputBar` block as the full-width `data-testid="gameboard-input-region"` (`w-full`); rendered `<HpPipScale>` after `<InputBar>` (narration → input → HP). Single edit serves BOTH the mobile (MobileTabView) and desktop (Dockview) layouts since both render `{inputBar}`.

**Tests:** 15/15 passing (GREEN) — 9 component + 6 wiring. Full UI regression: **1601/1601 passing, 0 failures** (no regression in GameBoard, CharacterPanel, edge-badge, location-tab, action-reveal). ESLint clean on both changed files. Pre-existing tsc errors (37) are in unrelated test fixtures (CharacterSheet.test, WorldPreview.test, etc.) — not in any file this story touched.

**Branch:** `feat/69-2-opening-gameboard-action-input-hp-pips` (pushed; commits `d32c11b` tests, `3be6070` impl)

**AC coverage:**
- AC-1 (full-width input under narrative): `gameboard-input-region` `w-full`, ordered after `.flex-1` content ✓
- AC-2 (co-located high-contrast HP pip scale): `input-hp-scale` adjacent to `input-bar`, pips + danger tone via theme tokens ✓
- AC-3 (responsive): present in both mobile + desktop layout paths ✓
- AC-4 (legible / matches state): `aria-label` + visible `HP cur/max`, reactive to `characters[]` ✓
- AC-5 (submit → state → HP reflect, wiring): `HpPipScale` rendered by GameBoard in production; reactive update test passes ✓

**Handoff:** To Architect (Major Houlihan) for spec-check.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (1 Minor mismatch; non-blocking)
**Mismatches Found:** 1 substantive + 2 already-logged Dev deviations confirmed

Structural gate (AC coverage, implementation-complete, deviation formatting) passed. Substantive read of the diff (`HpPipScale.tsx` + 7-line GameBoard wiring) against each AC:

- **AC-1 (full-width input under narrative):** Aligned. `gameboard-input-region` carries `w-full` and is ordered after the `.flex-1` content region in both layouts.
- **AC-2 (co-located high-contrast HP pip scale):** Aligned *except* the large-`hp_max` overflow case — see mismatch below.
- **AC-3 (responsive):** Partially aligned — same overflow caveat (mobile horizontal-scroll edge case).
- **AC-4 (legibility / matches state):** Aligned. `aria-label="HP {cur} of {max}"` + visible `HP {cur}/{max}`, props-driven reactivity verified by the rerender test.
- **AC-5 (submit → state → HP reflect, wiring):** Aligned. `HpPipScale` is a production consumer rendered by GameBoard inside the input region.

**Mismatch 1 — HP pip row has no overflow handling at large `hp_max`** (Missing in code — behavioral, **Minor**)
  - Spec: context-story-69-2.md, AC-2 ("hp_max large — no overflow; pips wrap or condense") and AC-3 ("mobile: full-width input still accessible, no horizontal scroll").
  - Code: `HpPipScale` renders the pip row as `<span className="flex gap-0.5">` with fixed `h-2 w-2` pips — no `flex-wrap`, no per-pip condense (`flex:1 1 0`), no `overflow` guard. The original `FolioEdgeTicks` it reuses handled this with `flex:1 1 0` per pip + `overflow:hidden`; that condensing behavior was dropped in the extraction. With ADR-114 ablative HP (30–40 max) on a ~360px mobile input region, ~40 fixed pips (~10px each) overflow horizontally — the exact "no horizontal scroll" case AC-3 protects for Alex. Tests pass because jsdom does not compute layout, so overflow is invisible to the suite.
  - **Recommendation: D — Defer** (with a recommended one-line fix). Rationale: non-breaking, manifests only at high `hp_max` on narrow viewports, and the fix is trivial — add `flex-wrap` (pips wrap to a second row) or restore the `flex:1 1 0` + `overflow-hidden` condense from `FolioEdgeTicks`. Bouncing a 3pt UI-polish story all the way back to green for one utility class is disproportionate, and jsdom cannot meaningfully assert the fix anyway (only class-presence). Recorded as a delivery finding so the Reviewer (Potter) sees it with the full diff and can require it at review if they judge it blocking for Alex's mobile path. **Not handing back** — Minor/non-breaking does not meet the Critical/Major hand-back bar.

**Mismatch 2 — standalone `HpPipScale` rather than extract-and-share from CharacterPanel** (Different — architectural, **Minor**; already logged by Dev)
  - Spec: Technical Guardrails recommended extracting `EdgeBadge`/`FolioEdgeTicks` and having CharacterPanel consume the shared component.
  - Code: standalone reimplementation of the idiom; CharacterPanel unchanged.
  - **Recommendation: D — Defer.** I accept Dev's logged rationale (blast-radius discipline, 1601 tests green, ACs don't require it). The pip/danger-threshold logic now lives in two places — acceptable short-term, but it's the same risk surface as Mismatch 1 (a threshold change must be mirrored). A single follow-up refactor can fold both: extract one shared component with overflow handling, consumed by both CharacterPanel and the input scale. Captured as a delivery finding.

**Mismatch 3 — HP placed after InputBar** (Trivial): aligned with AC-1's "narration → input → HP" hierarchy. No action.

**Decision:** Proceed to verify (TEA). Drift is Minor and non-blocking; both deferrals are documented with concrete follow-up guidance and surfaced to the Reviewer.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`src/components/HpPipScale.tsx`, `src/components/GameBoard/GameBoard.tsx`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | The `HpPipScale` reimplementation of CharacterPanel's private `FolioEdgeTicks` idiom is intentional and justified — those helpers are unexported; making HpPipScale depend on them (or exporting the Folio design system) would be inappropriate coupling. LOW confidence, not worth flagging. |
| simplify-quality | clean | Naming, typing, null-safety, theme-token usage, `data-testid` conventions, `DANGER_RATIO` const, and GameBoard wiring all conform to project patterns. (Its "no unit tests exist" note is incorrect — the 9-case `hp-pip-scale-component-69-2.test.tsx` covers the component; the teammate did not inspect the test file.) |
| simplify-efficiency | clean | Component is appropriately scoped; guards (`hp_max > 0`, `Math.max(0, hp_max)`) are intentional. Confirmed the large-`hp_max` pip-overflow is a system/spec concern (already the Architect's logged spec-check finding), not local over-engineering. |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations requiring action (reuse-duplication is documented as a deferred Architect/Dev follow-up)
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** Story tests 15/15 passing (RUN_ID 69-2-tea-verify). Full UI regression 1601/1601 passing at GREEN (RUN_ID 69-2-dev-green-full); no code changed since, so the state holds. ESLint clean on both changed files. The 37 tsc errors are pre-existing fixtures in untouched files.

**Outstanding (carried to Reviewer):** The Architect's deferred AC-2/AC-3 overflow gap (`HpPipScale` pip row lacks `flex-wrap`/condense at large `hp_max`). I concur it is non-blocking for the tested behavior and cannot be asserted in jsdom (no layout engine); Colonel Potter to make the final ship/hold call with the full diff.

**Handoff:** To Reviewer (Colonel Potter) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 1601 tests green, 0 smells, ESLint clean, tsc clean on both branches |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — edge paths assessed by Reviewer (see Rule Compliance + observations) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — fallback path assessed by Reviewer |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — test quality assessed by Reviewer (15 tests, concrete assertions) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — comments accurate (verified) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — types assessed by Reviewer |
| 7 | reviewer-security | Yes | findings | 2 (both low-confidence) | confirmed 1 (Low, converges w/ overflow), dismissed-as-framed 1 (leak→Low correctness) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — also covered by TEA verify simplify fan-out (all clean) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — rule-by-rule done by Reviewer (see Rule Compliance) |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents` and assessed directly by Reviewer)
**Total findings:** 2 confirmed (1 Medium overflow [mine+Architect], 1 Low DoS-resilience [SEC]), 1 downgraded (SEC info-leakage → Low correctness), 0 blocking

## Reviewer Assessment

**Verdict:** APPROVED

This is a clean, minimal, well-tested 3-pt UI change: an 87-line presentational `HpPipScale` + a 7-line wiring seam in `GameBoard.tsx`. 1601/1601 tests green, ESLint clean, tsc clean on the changed files. No Critical or High issues. Two non-blocking Medium/Low items are documented with a single converging 2-line fast-follow fix.

**Data flow traced:** server `PARTY_STATUS` → `useStateMirror` → `GameStateProvider` → `GameBoard.characters` prop → `HpPipScale` → local player resolved by `currentPlayerId` → pips + `aria-label`. Safe: the component renders only typed numeric `hp`/`hp_max` into text/attributes; no innerHTML, no casts. (Reactivity verified by the rerender test, AC-4/AC-5.)

**Pattern observed:** reuses the CharacterPanel HP idiom (HP cur/max label, one pip per max unit, ≤25% destructive tone) via ADR-079 theme tokens — `HpPipScale.tsx:48-79`. Wired as a real production consumer at `GameBoard.tsx:571`.

**Error handling:** division guarded (`hp_max > 0 ? … : 1`, `HpPipScale.tsx:48`), `Math.max(0, hp_max)` floors negative max, empty party guarded (`{local && …}`, line 39). No throwing paths.

### Confirmed findings (subagent-tagged)

- **[SEC]/[SIMPLE] (Medium, non-blocking) — pip row overflows / unbounded render at large `hp_max`.** `HpPipScale.tsx:65-66` renders `Array.from({length: cap})` fixed `h-2 w-2` pips in a non-wrapping `flex gap-0.5`, with no `flex-wrap`, condense, or ceiling. Two consequences converge here: (1) the Architect's AC-2/AC-3 overflow gap — at ADR-114 HP (~30–40) on a ~360px mobile region the row overflows horizontally, violating AC-3 "no horizontal scroll" for Alex; (2) the security subagent's unbounded-render concern — a corrupted/compromised server `hp_max` (e.g. 1e6) would allocate millions of spans and freeze the tab. **Fix (single, ~2 lines):** add `flex-wrap` to the pip container AND a render ceiling `const renderCap = Math.min(cap, 100)` (fall back to the already-visible `HP {hp}/{hp_max}` text beyond it). Severity Medium: non-breaking, viewport+HP-conditional, and the unbounded pattern is **pre-existing in `FolioEdgeTicks`** (`CharacterPanel.tsx:757`) — 69-2 introduces no new risk class. Confidence on the DoS is low (needs server compromise/corrupt save). Carried as a delivery finding + folded into the planned shared-component refactor.
- **[SEC] (Low, non-blocking) — `?? characters[0]` fallback can show the wrong character's HP.** `HpPipScale.tsx:32`: when `currentPlayerId` is undefined/unmatched (e.g. partially-hydrated MP state) the scale falls back to `characters[0]`. **Dismissed as an info-*leak*** — party HP is NOT hidden state; the `edge-badge-party-status-wiring` test renders every party member's HP to all clients via PARTY_STATUS, so no confidentiality boundary is crossed. Retained as a Low *correctness* note: the fallback is the correct default for the single-PC opening case (where `characters[0]` IS the local player), so I do not require a change; if MP partial-hydration proves to flash a peer's HP at the input, the fix is `return null` when unmatched.

### Other-domain tags (subagents disabled — assessed by Reviewer)

- **[EDGE]:** boundary cases enumerated — `hp=0` (all empty + danger, no crash), `hp=hp_max` (all filled), `hp>hp_max` (fill clamped to `cap`), negative hp (all empty), empty party (`{local && …}` guards, container still renders). All graceful. The only unhandled boundary is the large-`hp_max` render, covered above.
- **[TEST]:** 15 tests, all with concrete assertions (exact pip counts, exact `aria-label` strings, danger class presence/absence). No vacuous `assert(true)`/`is*`-on-always-null. Split into a component-contract file + a GameBoard wiring file (the wiring file loads independently → genuine per-assertion RED was proven). The wiring test satisfies the project "every suite needs a wiring test" rule. No implementation-coupling beyond the agreed testid contract.
- **[TYPE]:** props typed via `HpPipScaleProps`/`CharacterSummary`; no `as any`, no `as unknown as T`, no non-null assertion. `currentPlayerId?` optional and handled. `local` nullable and guarded.
- **[DOC]:** the component docblock and the GameBoard inline comment accurately describe behavior (player-facing, no OTEL, reuse of the idiom, input→HP hierarchy). No stale/misleading comments.
- **[SILENT]:** no swallowed errors or empty catches; the one fallback (`?? characters[0]`) is intentional and documented, addressed above.

### Rule Compliance (TypeScript lang-review checklist — exhaustive on the diff)

| Rule | Instances checked | Verdict |
|------|-------------------|---------|
| #1 type-safety escapes (`as any`, `!` on nullable, double-cast) | HpPipScale (all), GameBoard wiring | Compliant — none present; `characters[0]` is array indexing, not `!` |
| #4 null/undefined (`??` vs `||` on falsy-valid, undefined handling) | `ratio` guard (line 48), `?? characters[0]` (line 32), `{local && …}` (line 39) | Compliant — `??` used correctly; `0` HP treated as a real value, not "missing" |
| #6 React/JSX (`key={index}`, hooks deps, `dangerouslySetInnerHTML`) | pip `key={pip-${i}}` (line 70); no hooks; no dangerouslySetInnerHTML | Compliant — index key is acceptable on a stateless, homogeneous, order-stable pip list (no per-item state to mis-associate); no XSS surface |
| #8 test quality (no `as any` in tests, meaningful asserts) | both test files | Compliant — concrete assertions, no `as any`, no vacuous checks |
| #10 input validation / no `as T` on untrusted JSON | HpPipScale props | Compliant — typed prop, no parse/cast; upstream PARTY_STATUS is the data source (out of diff) |
| #12 performance (large render in hot path) | `Array.from({length: cap})` (line 66) | **Partial** — no upper bound; see Medium finding (matches pre-existing FolioEdgeTicks pattern) |
| SOUL/ADR-104-105 perception (no leaking hidden state) | HpPipScale rendering, GameBoard prop pass | Compliant — party HP is shared (not hidden); server is the firewall per ADR-104/105; UI trusts the filtered array |
| ADR-079 theme tokens (no hardcoded hex) | all color classes (lines 59, 77-79) | Compliant — `text-destructive`, `var(--primary)`, `var(--border)`; no hex |

### Verified-good (evidence-cited)

- **[VERIFIED] Wiring is real, not just unit-tested** — `GameBoard.tsx:54` imports `HpPipScale`; `GameBoard.tsx:571` renders it inside the `gameboard-input-region` (`GameBoard.tsx:533`), which is the shared `inputBar` slot rendered by BOTH MobileTabView and the desktop input-area. Non-test production consumer confirmed. Complies with the project wiring rule.
- **[VERIFIED] Accessibility** — group carries `aria-label="HP {hp} of {hp_max}"` (`HpPipScale.tsx:55`), decorative pips are `aria-hidden` (`HpPipScale.tsx:65`); a screen reader reads one HP string, not 30 pips. Matches the EdgeBadge a11y convention.
- **[VERIFIED] Theme/high-contrast** — colors are ADR-079 tokens only (`HpPipScale.tsx:59,77-79`); danger uses `text-destructive`/`bg-destructive`, matching EdgeBadge's tested `/destructive/` convention.
- **[VERIFIED] tsc on changed files** — preflight reports 0 tsc errors on both `develop` and the feature branch; the changed files introduce no type errors. (Note the discrepancy vs the earlier full-suite run's "37 fixture errors" — preflight could not reproduce them; immaterial to this verdict since changed files are clean.)

### Devil's Advocate

Let me argue this code is broken. The headline charge: **the feature visibly fails on the exact device and user it was written for.** This story exists to help Alex on a phone and to make HP legible for Sebastien/Jade. Yet the co-located scale renders one fixed-size DOM pip per HP point in a non-wrapping flex row with no ceiling. A first-level character under ADR-114 ablative HP can sit at 30–40 max. At ~10px per pip plus the "HP 40/40" label, that's ~460px of content shoved into a ~360px phone — the input region overflows, and because nothing sets `overflow`, the whole gameboard can gain a horizontal scrollbar. The story's own AC-3 says "no horizontal scroll to reach it." So on the primary device, for realistic data, the feature breaks its own acceptance criterion the moment a player has a healthy character. That is not a contrived edge case; it could be the *default* first-screen experience.

A malicious or merely buggy server makes it worse: `hp_max` is a `number` straight off the wire with no client ceiling, fed to `Array.from({length: cap})`. Send `hp_max: 1_000_000` (corrupt save, replay attack, or a server bug) and the tab allocates a million spans and freezes — a denial of service against the player, mid-session. A confused user wouldn't understand why their game locked up.

What about state churn? On reconnect, `currentPlayerId` may briefly be undefined while the mirror rehydrates; the `?? characters[0]` fallback then paints *some other* party member's HP at the local input for a frame or two. Not a confidentiality breach (party HP is public), but a momentary lie about whose vitality you're looking at — exactly the kind of "winging it" the project distrusts, except in the UI.

How much of this actually lands? The overflow is real but bounded and trivially fixable; the DoS mirrors a pattern already shipping in `FolioEdgeTicks`, so it's a latent class issue, not a 69-2 regression; the fallback flash is transient and harmless to confidentiality. None rise to data corruption or a security breach. So the devil's advocate sharpens the **Medium overflow + render-cap** into the one thing worth fixing soon — but uncovers nothing that should block a 3-pt polish merge whose tested behavior is correct and fully wired.

**Conclusion:** No Critical/High. The convergent overflow/render-cap is a genuine Medium worth a fast 2-line follow-up (and a natural rider on the already-planned shared-pip-component refactor). Approving with that documented.

**Handoff:** To SM (Hawkeye) for finish-story.

## Workflow Tracking

**Workflow:** TDD (phased)
**Phase:** finish
**Phase Started:** 2026-05-27T07:34:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-27 | 2026-05-27 | — |
| red | 2026-05-27 | (in progress) | — |

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): The `testing-runner` subagent wrote its test-session report to `.session/69-2-session.md`, OVERWRITING the workflow session file (SM Assessment, story context, deviations). I reconstructed the session from in-conversation history. Affects the `testing-runner` agent / its RUN_ID→output-path logic (`.pennyfarthing/agents/testing-runner.md`) — it must not write to `.session/{story-id}-session.md`; that path is the workflow session, not a scratch report target. *Found by TEA during test design.*
- **Gap** (non-blocking): SM `complete-phase` advanced setup→red while `sprint/context/context-story-69-2.md` and `context-epic-69.md` did not exist; the RED context gate then blocked TEA. The `sm-setup-exit` gate's context-creation recovery did not run/persist. Affects the SM setup→handoff path (context must exist before RED). Context was authored by the Architect this session as a recovery. *Found by TEA during test design.*
- **Improvement** (non-blocking): `EdgeBadge` and `FolioEdgeTicks` are module-private in `CharacterPanel.tsx`. To satisfy "co-located HP scale" without duplicating the pip idiom, Dev should extract them into the shared `HpPipScale` and have CharacterPanel consume it — one implementation, two mount points. Affects `src/components/CharacterPanel.tsx` + new `src/components/HpPipScale.tsx`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): Deferred the TEA shared-extraction Improvement. `HpPipScale` reuses the CharacterPanel HP idiom but is a separate implementation; CharacterPanel's private `FolioEdgeTicks`/`EdgeBadge` are unchanged. The pip/threshold logic now lives in two places. A follow-up can unify them (extract into `HpPipScale`, have CharacterPanel consume it) — pure refactor, fully covered by existing tests. Affects `src/components/CharacterPanel.tsx` + `src/components/HpPipScale.tsx`. *Found by Dev during implementation.*
- **Question** (non-blocking): The co-located scale shows only the LOCAL player's HP (per context Assumptions, single-PC opening). If the table wants the full party's HP glanceable at the input in MP, that's a deliberate scope expansion for a future story — `HpPipScale` already takes the full `characters[]` array, so it's a small change. Affects `src/components/HpPipScale.tsx`. *Found by Dev during implementation.*

### Architect (spec-check)
- **Gap** (non-blocking): `HpPipScale` pip row has no overflow handling at large `hp_max`. AC-2/AC-3 require "no overflow — pips wrap or condense" and "mobile: no horizontal scroll", but the row is a fixed-pip `flex gap-0.5` with no `flex-wrap`/condense/overflow. At ADR-114 HP (30–40) on a narrow mobile input region this overflows horizontally — Alex's exact responsive case. Recommended fix: add `flex-wrap` to the pip container, or restore `FolioEdgeTicks`' `flex:1 1 0` + `overflow-hidden` condense. Affects `src/components/HpPipScale.tsx:65`. Deferred (Minor, non-breaking); Reviewer to confirm acceptability. *Found by Architect during spec-check.*
- **Improvement** (non-blocking): Fold the two open pip-related items into one follow-up refactor — extract a single shared HP-pip component (with overflow handling) consumed by both `CharacterPanel` and `HpPipScale`, eliminating the duplicated pip/threshold logic. Affects `src/components/CharacterPanel.tsx` + `src/components/HpPipScale.tsx`. *Found by Architect during spec-check.*
- No new upstream findings during test verification. Simplify fan-out (reuse/quality/efficiency) returned clean; the Architect's deferred overflow gap is carried to the Reviewer. *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking, recommended fast-follow): `HpPipScale` pip row needs a render ceiling + wrap. A single ~2-line change — `flex-wrap` on the pip container at `src/components/HpPipScale.tsx:65` plus `const renderCap = Math.min(Math.max(0, hp_max), 100)` at line 50 (fall back to the visible `HP cur/max` text beyond the cap) — resolves BOTH the AC-2/AC-3 mobile overflow (Architect's finding) AND the unbounded-`Array.from` client-DoS risk (reviewer-security finding) at once. Affects `src/components/HpPipScale.tsx`. Best folded into the planned shared-pip-component refactor. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The same unbounded-pip-render pattern pre-exists in `CharacterPanel.tsx:757` (`FolioEdgeTicks`); the shared-component refactor should apply the render cap there too. Affects `src/components/CharacterPanel.tsx`. *Found by Reviewer during code review.*
- **Question** (non-blocking): Process — the verify-phase full-suite run reported ~37 tsc errors in unrelated fixtures, but reviewer-preflight found 0 tsc errors on both `develop` and the feature branch. Worth confirming which testing-runner invocation was inaccurate so future tsc gating is trustworthy. Affects `.pennyfarthing/agents/testing-runner.md` (tsc reporting). *Found by Reviewer during code review.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Defined a concrete DOM/testid contract the ACs left open**
  - Spec source: context-story-69-2.md, AC-1 / AC-2 / AC-4 / AC-5
  - Spec text: "Action input bar is full-width below the narrative area"; "Renders party HP as a visual pip/dot scale per character … Positioned adjacent to or inline with the action input"; "each character pip label or tooltip shows current/max"
  - Implementation: Tests pin specific testids/attributes — `gameboard-input-region` (`w-full`), `input-hp-scale`, `hp-pip-group-{player_id}` with `aria-label="HP {cur} of {max}"`, per-pip `data-testid="hp-pip"` + `data-filled`, and danger via className `/destructive/`. The ACs name no DOM; TEA chose these to make "full-width" and "co-located" testable, aligning the aria-label and ≤25% danger threshold with the existing `EdgeBadge` convention (`character-edge-badge`, `aria-label="HP N of M"`).
  - Rationale: Layout/co-location claims need a stable DOM anchor to assert; reusing the established EdgeBadge a11y string and threshold keeps screen-reader output and danger behavior consistent across surfaces. Dev may rename internals but must preserve these externally-observable hooks (the tests are the contract).
  - Severity: minor
  - Forward impact: none (sibling 69-1 is dice-only; no shared surface)

- **Component-level test resolves the local player's HP, single-PC focus**
  - Spec source: context-story-69-2.md, AC-2 ("per character") + Assumptions ("opening gameboard uses a single active PC … the co-located scale shows the player's own character")
  - Spec text: "Renders party HP as a visual pip/dot scale per character"
  - Implementation: Tests assert the co-located scale renders the LOCAL player's group (resolved by `currentPlayerId`, fallback first character); multi-PC simultaneous rendering is not asserted.
  - Rationale: The context's own Assumptions section scopes the opening co-located scale to the player's own character; full multi-PC rendering near the input is out of scope and would crowd the input on mobile. If Dev renders all party members, these tests still pass (they assert the local group exists), so this is a floor, not a ceiling.
  - Severity: minor
  - Forward impact: none

### Dev (implementation)
- **Built `HpPipScale` standalone instead of extracting `EdgeBadge`/`FolioEdgeTicks` from CharacterPanel**
  - Spec source: context-story-69-2.md, Technical Guardrails + Delivery Findings (TEA Improvement, 69-2)
  - Spec text: "extract them into the shared `HpPipScale` and have CharacterPanel consume it — one implementation, two mount points"
  - Implementation: Created `src/components/HpPipScale.tsx` as a new, standalone presentational component that REUSES the same idiom (HP cur/max label, one pip per max-HP unit, destructive tone at ≤25%, ADR-079 theme tokens) but does NOT modify CharacterPanel or import its private `EdgeBadge`/`FolioEdgeTicks`.
  - Rationale: Minimalist-discipline + blast-radius control. The ACs/tests do not require CharacterPanel to consume the new component; refactoring CharacterPanel would touch a heavily-tested surface (edge-badge-party-status-wiring, character-panel sidebar tests) for no test-driven benefit during GREEN. The shared-extraction is a clean follow-up that can be done without re-deriving behavior. All 1601 UI tests stay green.
  - Severity: minor
  - Forward impact: minor — the pip-rendering idiom now exists in two places (CharacterPanel's private `FolioEdgeTicks` and `HpPipScale`). A future refactor can unify them; until then, a change to the danger threshold or pip semantics must be mirrored in both. Logged as a Dev delivery finding for the Reviewer/Architect to weigh.

- **Placed the HP scale after the InputBar (input → HP), not before**
  - Spec source: context-story-69-2.md, AC-1
  - Spec text: "Clear visual hierarchy: narration → input → HP state"
  - Implementation: `<HpPipScale>` renders immediately AFTER `<InputBar>` inside the shared `gameboard-input-region`, matching the stated narration → input → HP ordering.
  - Rationale: Honors the AC-1 hierarchy literally; the wiring tests assert only co-location (both inside the region) and DOM order relative to the narrative content, not the input-vs-HP order, so this is spec-faithful and test-safe.
  - Severity: trivial
  - Forward impact: none

### Reviewer (audit)
- **TEA — concrete DOM/testid contract** → ✓ ACCEPTED by Reviewer: sound. Layout/co-location ACs need a stable DOM anchor to be testable, and reusing the EdgeBadge `aria-label`/threshold convention keeps a11y and danger behavior consistent across surfaces. Verified the contract matches the implementation.
- **TEA — single-PC local-player focus** → ✓ ACCEPTED by Reviewer: matches the context Assumptions; the floor-not-ceiling framing is correct (rendering all party members would still pass). Carried Dev's MP-expansion question forward as non-blocking.
- **Dev — standalone `HpPipScale` vs extract-from-CharacterPanel** → ✓ ACCEPTED by Reviewer: blast-radius discipline is the right call for GREEN; the duplication is documented and slated for the shared-component refactor follow-up. I added that the same render-cap fix should land in `FolioEdgeTicks` during that refactor.
- **Dev — HP placed after InputBar** → ✓ ACCEPTED by Reviewer: literally honors AC-1's "narration → input → HP" hierarchy; no test constrains the order, spec-faithful.
- No UNDOCUMENTED deviations found — the implementation matches the spec and the agreed testid contract; the only substantive gap (large-`hp_max` overflow/render-cap) was already logged by the Architect and is captured as a non-blocking Reviewer delivery finding.
  - Forward impact: none

### Architect (reconcile)

**Entry-verification pass:** All prior deviation entries (TEA ×2, Dev ×2) were checked against the spec sources. Spec source paths (`context-story-69-2.md`) exist; quoted spec text is accurate against the AC list in this session; implementation descriptions match the shipped code (`HpPipScale.tsx`, `GameBoard.tsx:533,571`); all six fields are present and substantive. The Reviewer audit stamped each ACCEPTED. No corrections needed.

**AC accountability:** All five ACs were implemented and tested — none were deferred or descoped (no AC-deferral table to reconcile). AC-2/AC-3 are met for normal HP ranges; their large-`hp_max` edge clause is the single deviation below.

**Missed-deviation pass — one entry added for audit completeness:**

- **AC-2/AC-3 large-`hp_max` overflow edge not handled (pip row lacks wrap/condense/render-cap)**
  - Spec source: context-story-69-2.md, AC-2 and AC-3
  - Spec text: AC-2 — "Renders party HP as a visual pip/dot scale per character … Positioned adjacent to or inline with the action input"; its expanded edge clause: "hp_max large (no overflow — pips wrap or condense)". AC-3 — "Mobile: full-width input still accessible (no horizontal scroll to reach it)".
  - Implementation: `HpPipScale` renders one fixed-size (`h-2 w-2`) pip per HP unit in a non-wrapping `flex gap-0.5` row (`src/components/HpPipScale.tsx:65-66`) with no `flex-wrap`, no per-pip condense, and no upper render bound. For normal HP the row fits; at ADR-114 ablative HP (~30–40) on a ~360px mobile viewport it overflows horizontally, and an out-of-range server `hp_max` would render an unbounded number of spans. The danger threshold, label, reactivity, and co-location are all correct — only the large-value edge is unhandled.
  - Rationale: Deferred deliberately at spec-check and confirmed at review as non-blocking (Minor/Medium, viewport+HP-conditional, the unbounded-render pattern pre-exists in `CharacterPanel.tsx:757` `FolioEdgeTicks`, and jsdom cannot regression-test layout overflow). The fix is a single ~2-line change (`flex-wrap` + `const renderCap = Math.min(Math.max(0, hp_max), 100)`) best folded into the planned shared-pip-component refactor, where it should also be applied to `FolioEdgeTicks`.
  - Severity: minor
  - Forward impact: minor — a follow-up story (shared HP-pip component with render-cap, consumed by both `CharacterPanel` and `HpPipScale`) should close this. Until then, high-HP characters on narrow viewports see horizontal overflow at the input.

**Reconcile verdict:** Deviation manifest complete and self-contained. No blocking deviations. Story is ready for SM finish.