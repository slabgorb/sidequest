---
story_id: "83-2"
jira_key: ""
epic: "83"
workflow: "tdd"
---
# Story 83-2: Standing Folio lobby — close AC8 gaps (880/560 breakpoints + reduced-motion) and design-divergence ratification

## Story Details
- **ID:** 83-2
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** ui (sidequest-ui)
- **Points:** 3
- **Priority:** p2

## Context

### Design Reference
Full UX design spec: `/Users/slabgorb/Projects/oq-4/docs/design/83-2-lobby-folio-followups.md`

### Scope Summary

Story 83-1 rebuilt `ConnectScreen` into "The Standing Folio" lobby and merged to develop (2026-06-03). This is a follow-up polish story closing two AC8 gaps that shipped incomplete, plus parked implementation items.

**AC8 Gaps (load-bearing):**

1. **Breakpoints diverge from spec** — 83-1 AC8 spec'd `<=880px` for single-column folio + two-up index grid, and `<=560px` for stacked commit row + full-width Start. Build shipped Tailwind defaults (768px / 640px). At 860px, the lobby is still two-column. Fix via arbitrary breakpoints (`max-[880px]:` / `max-[560px]:`) or Tailwind config registration.

2. **`prefers-reduced-motion` unhandled** — 83-1 AC8 spec'd reduced-motion respected. Reality: no `prefers-reduced-motion` media query anywhere in src; unguarded `animate-spin` (WorldPreview image spinner) and `animate-pulse` (loading skeleton + ConnectScreen pulse text) ignore reduce. Guard with `motion-reduce:animate-none` or gate behind `@media (prefers-reduced-motion: no-preference)`.

**Design Divergences (RESOLVED — Keith, 2026-06-03 — zero code):**

- CurrentSessions null-on-empty is KEPT (no "No lanterns lit here tonight." empty-state copy)
- Rules-in-commit-row placement is ACCEPTED (fine for now, ADR-135 tension deferred)

**Parked Items (still in scope):**

1. Self-host Pirata One font for the wordmark (replaces house-serif fallback)
2. Add `console.warn` to silent catches (`/dev/scenes`, `loadSavedState`, `saveState`) per No-Silent-Fallbacks
3. Add `data-testid="lobby-accent-root"` to `.lobby-folio` root and harden AC7 accent test against it
4. Guard `effectiveOpenGenre` against a stale genre whose pack was removed

**Minor Observed Issue:**

- Cold-mount flash-of-error: "Could not load worlds. Is the server running?" appears before worlds fetch settles. Show neutral loading state instead until fetch resolves or genuinely fails.

### Non-Scope (per design spec)

- Hero art stays atmospheric placeholders (per designer's note)
- No full genre re-skin — accent shift only
- No new below-the-fold sections beyond what design defined

### Acceptance Criteria

1. Breakpoints match 83-1 AC8 spec, not Tailwind defaults: folio collapses to single-column + two-up index grid at <=880px, and the commit row stacks with full-width Start at <=560px. Runtime-verified at the boundaries (881 vs 880, 561 vs 560).

2. Reduced-motion respected: animate-spin (WorldPreview image spinner) and animate-pulse (loading skeleton + ConnectScreen pulse text) are guarded with motion-reduce: (or gated behind prefers-reduced-motion: no-preference). Under an emulated prefers-reduced-motion: reduce, no looping animation runs and all content has a visible end-state as its base (no opacity:0-stuck cards).

3. Parked items resolved or explicitly deferred with rationale: (a) Pirata One self-hosted for the wordmark (replaces house-serif fallback); (b) console.warn added to the three silent catches (/dev/scenes, loadSavedState, saveState) per No-Silent-Fallbacks; (c) data-testid=lobby-accent-root added and AC7 accent test asserts against it; (d) effectiveOpenGenre guarded against a stale genre whose pack was removed.

4. Cold-mount worlds fetch shows a loading state (not the 'Could not load worlds. Is the server running?' error) until the fetch resolves or genuinely fails; the error copy only appears on a real failure.

### Related Stories

- **83-1** (done, merged develop) — Rebuilt ConnectScreen as the Standing Folio lobby; established the baseline

## Sm Assessment

Setup complete and routed to tea for the RED phase. This is a tightly-scoped UI-only follow-up to the merged 83-1 Standing Folio lobby, driven by a concrete UX verification pass (Alex/ux-designer, 2026-06-03) with a full design spec at `docs/design/83-2-lobby-folio-followups.md`.

**Routing rationale:** 4 ACs, all runtime-observable in the React client — well-suited to tdd. The two load-bearing ACs (responsive breakpoints, reduced-motion) are testable via Playwright viewport + emulated `prefers-reduced-motion`; the parked items (AC3) and cold-mount loading state (AC4) are testable against component behavior.

**Scope guardrails for downstream agents:**
- AC1/AC2 are the load-bearing gaps — breakpoints at **880/560** (not Tailwind 768/640), and reduced-motion guards on the existing `animate-spin`/`animate-pulse`.
- **Do NOT implement** the two RESOLVED divergences (CurrentSessions null-on-empty stays; Rules-in-commit-row placement accepted). These are zero-code decisions from Keith (2026-06-03). Touching them is out of scope.
- Accessibility framing: reduced-motion serves the household's low-tolerance users and is plain correctness, not a primary-audience trade. Breakpoint fidelity keeps the lobby usable on smaller surfaces.

**Open question for tea:** AC1 requires *runtime* boundary verification (881 vs 880, 561 vs 560). Confirm the test harness can drive viewport resizes and assert layout at the boundary, rather than only asserting class presence — class-presence tests are coupling-prone for arbitrary Tailwind breakpoints.

No blockers. Branch `feat/83-2-standing-folio-ac8-gaps` is live in sidequest-ui off develop.

## TEA Assessment

**Tests Required:** Yes

**Test Files:**
- `sidequest-ui/src/screens/__tests__/ConnectScreen.ac8.test.tsx` — 17 tests (14 RED + 3 green regression-guards) covering all four ACs + parked items + an App wiring test.

**Tests Written:** 17 tests covering 4 ACs (AC1–AC4) and four parked items (AC3a–d).
**Status:** RED (14 failing, ready for Dev). 3 companion tests pass as regression-guards (Pirata `@font-face` still declared; no opacity:0-stranded shell node; load-error still shows on genuine `genreError=true`).

**Pre-flight:** Before writing tests I closed a context gap — `sm-setup` created the session/branch but **not** the context docs. I authored `sprint/context/context-epic-83.md` + `context-story-83-2.md` (both validate clean) via `/pf-context`, solo (design spec is already specialist UX content).

### Coverage map (test → AC)

| AC | Test(s) | Verifies | Status |
|----|---------|----------|--------|
| AC1 breakpoints | folio single-col @880; Start full-width @560 | folio card drops `md:`(768) → 880 collapse; Start drops `sm:`(640) → 560 full-width | RED |
| AC2 reduced-motion | spinner `animate-spin`; frame `animate-pulse`; connecting pulse | each looping animation carries `motion-reduce:animate-none` | RED |
| AC2 (guard) | no opacity:0-stranded shell node | end-state-as-base rule holds for shell markup | green guard |
| AC3a Pirata wordmark | `.lobby-wordmark` font-family | bound to "Pirata One", not house-serif fallback | RED |
| AC3a (guard) | Pirata `@font-face` declared | self-hosted face still present (no Google CDN) | green guard |
| AC3b warn | /dev/scenes reject → warn; loadSavedState throw → warn; saveState (source grep) | all three silent catches warn per No-Silent-Fallbacks | RED |
| AC3c testid | `.lobby-folio` root carries `data-testid=lobby-accent-root`; hardened accent shift via testid | accent root tagged + accent retargets on selection | RED |
| AC3d stale genre | removed-pack saved genre → first live genre opens | guard sanitizes stale `genreSlug` (also fixes a crash — see findings) | RED |
| AC4 cold-mount | loading state (not error) while genres in-flight; App wiring | empty+`!genreError` = loading, not failure | RED |
| AC4 (guard) | genuine failure (`genreError=true`) shows error | error still surfaces on real failure | green guard |

### Contract test-hooks the Dev must expose

- `data-testid="lobby-accent-root"` on the `.lobby-folio` root (AC3c).
- `data-testid="lobby-worlds-loading"` — neutral cold-mount loading state (AC4).

### Rule Coverage (typescript.md lang-review)

| Rule | Test / enforcement | Status |
|------|--------------------|--------|
| #4 null/undefined (`?? ` not `||`) | cold-mount loading distinguishes empty-vs-failed without truthiness traps | covered by AC4 |
| #6 React/JSX (no stranded a11y motion) | reduced-motion end-state guard (AC2) | covered |
| #8 test quality | every test asserts a meaningful value; no `let _=`, no `assert(true)`; 3 deliberate green guards documented | self-checked |
| #11 error handling (No Silent Fallbacks) | AC3b — all three swallowing catches must warn | covered |

**Rules checked:** 4 of 13 lang-review rules are materially applicable to this UI-polish story and have coverage; the rest (enums, generics, async, bundle, module decl) don't apply to the change surface.
**Self-check:** 0 vacuous tests. The 3 green tests are intentional regression-guards, each asserting a concrete value.

**Verification method note:** AC1/AC2 are **runtime CSS behaviors** that jsdom cannot evaluate, and `sidequest-ui` ships **no Playwright/browser harness** (`vitest run` only). These tests assert the static proxy (correct breakpoint numbers + `motion-reduce:` guards present in className/CSS), not observed layout/animation. See Design Deviations + Delivery Findings.

**Handoff:** To Dev (Agent Smith) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 17/17 AC8 tests passing (GREEN). Full UI suite: **1770 passing / 183 files**, zero failures. Lint clean, `tsc --noEmit` clean.
**Branch:** `feat/83-2-standing-folio-ac8-gaps` (pushed to origin).

**Files Changed:**
- `sidequest-ui/src/screens/ConnectScreen.tsx` — AC1 breakpoints (folio→single-col @880, divider + below-fold grid aligned to 880; commit row stacks + full-width Start @560); AC2 connecting-pulse `motion-reduce` guard; AC3b `console.warn` on three catches; AC3c `data-testid="lobby-accent-root"`; AC3d `validGenreSlug` sanitization; AC4 split `showGenreError`/`showWorldsLoading` + neutral loading branch.
- `sidequest-ui/src/screens/lobby/WorldPreview.tsx` — AC2 `motion-reduce:animate-none` on the image spinner + loading-skeleton pulse.
- `sidequest-ui/src/styles/lobby-folio.css` — AC3a `.lobby-wordmark` bound to self-hosted "Pirata One"; stale note rewritten.
- `sidequest-ui/src/screens/__tests__/ConnectScreen.ac8.test.tsx` — fixed the loadSavedState warn test's spy target (instance, not `Storage.prototype`) for the jsdom localStorage polyfill.

**Mechanism notes:**
- Breakpoints use Tailwind v4 arbitrary values (`max-[880px]:`, `min-[881px]:`, `max-[560px]:`) — no `tailwind.config` exists in v4; arbitrary values keep the 880/560 numbers literal and reviewable.
- AC3d: the stale-genre guard is a derived `validGenreSlug` (`genreSlug && genres[genreSlug] ? genreSlug : null`) used for every *presentation/derived* lookup (accent, archetype, lore/rules links, currentPack, effectiveOpenGenre). The raw `genreSlug` state is retained for the start/save paths, which only fire on a live user selection. This fixes both the `getArchetypeForGenre` crash and the wedged-open accordion in one place.
- AC4: no new prop — `genreError=false` + empty catalogue is the unambiguous in-flight signal (App sets `genreError=true` on failure incl. empty-response).

**Self-review:** Code wired (ConnectScreen is route-mounted in App; App wiring test green). Follows existing lobby patterns (testid hooks, Tailwind utility style). All ACs met. Error handling added per No-Silent-Fallbacks. No debug code, no stubs.

**Verification caveat (unchanged from TEA):** AC1/AC2 are runtime CSS behaviors proven here only by static class/CSS proxy — no Playwright harness in-repo. Visual runtime verification deferred to playtest/review (TEA Delivery Finding).

**Handoff:** To TEA (The Architect) for the verify phase (simplify + quality-pass).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (2 documented, non-blocking deviations — no drift requiring rework)
**Mismatches Found:** 2 (both already logged; neither needs a code hand-back)

Verified each AC against the committed diff (`git diff develop...HEAD`); code matches the Dev Assessment claim-for-claim:
- **AC1** — `max-[880px]:grid-cols-1` on the folio card, `min-[881px]:` on the pane divider + below-fold grid, `max-[560px]:` stack + full-width Start. Numbers literal and reviewable. ✓
- **AC2** — `motion-reduce:animate-none` on the WorldPreview spinner, loading-skeleton pulse, connecting-state pulse, and the new loading pulse; no new entrance animation added, so end-state-as-base holds. ✓
- **AC3a** — `.lobby-wordmark` bound to `"Pirata One"` (self-hosted via the existing R2 `@font-face`, project-standard "self-host"). ✓
- **AC3b** — `console.warn` on all three catches (loadSavedState, saveState, /dev/scenes). ✓
- **AC3c** — `data-testid="lobby-accent-root"` on the accent root. ✓
- **AC3d** — `validGenreSlug` sanitization across all derived lookups. ✓
- **AC4** — `showGenreError`/`showWorldsLoading` split + `lobby-worlds-loading` neutral state; correctly wired to App's `genreError` semantics (empty-but-successful → `genreError=true`, so no infinite-loading path). ✓

**Mismatch 1 — AC3d guard is broader than the parked-item text** (Extra in code — Behavioral, Minor)
  - Spec: "guard `effectiveOpenGenre` against a stale genre."
  - Code: a derived `validGenreSlug` routes accent, archetype, lore/rules, currentPack, AND effectiveOpenGenre through the catalogue check.
  - Recommendation: **A — accept/update spec.** The narrower guard would have left the `getArchetypeForGenre` crash (TEA's finding) and a dead accent/broken links. Single-point sanitization is the architecturally correct fix. Endorsed.

**Mismatch 2 — AC1 verified by static proxy + "two-up index grid" wording is ambiguous** (Ambiguous spec / Different verification — Cosmetic, Trivial)
  - Spec: "two-up index grid at ≤880px ... runtime-verified at the boundaries."
  - Code: page-wide single→two-column transition aligned to 880 (below-fold two-up *above* 880); breakpoint behavior proven by className/CSS proxy, not a real viewport (no Playwright in-repo).
  - Recommendation: **D — defer to runtime review.** Both the wording interpretation and true boundary verification belong to a playtest/e2e pass (already a Delivery Finding). No code change warranted now.

**Reuse note:** No new infrastructure introduced — the change reuses the existing lobby testid-hook convention, Tailwind utility styling, and the App-driven `genres`/`genreError` prop contract. No new component, hook, or prop. Consistent with pragmatic-restraint.

**Decision:** Proceed to review (TEA verify). No hand-back to Dev.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (no code change since the GREEN commit; full UI suite 1770/183 green, lint + `tsc --noEmit` clean).

### Simplify Report

**Teammates:** reuse, quality, efficiency (3 spawned in parallel)
**Files Analyzed:** 4 (ConnectScreen.tsx, WorldPreview.tsx, ConnectScreen.ac8.test.tsx, lobby-folio.css)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 — `validGenreSlug`, the three `console.warn` catches, and motion-reduce guards are appropriately scoped; no cross-file duplication or missing abstraction |
| simplify-quality | clean | 0 — naming/dead-code/architecture all sound; follows existing lobby patterns |
| simplify-efficiency | clean | 0 — no over-engineering; every addition maps directly to an AC |

**Applied:** 0 high-confidence fixes (nothing to apply)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** All passing (lint clean, typecheck clean, 1770 tests green). No simplify changes → no regression re-run needed.
**Handoff:** To Reviewer (The Merovingian) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (174 scoped tests green, 0 lint errors, 0 type errors) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 3 (2 medium, 1 low) | confirmed 3, dismissed 0, deferred 3 (all non-blocking, pre-existing/out-of-scope) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (verify-phase simplify fan-out already ran clean ×3) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (Rule Compliance assessed manually below) |

**All received:** Yes (2 enabled returned; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 3 confirmed (all non-blocking), 0 dismissed, 3 deferred to follow-up

## Reviewer Assessment

**Verdict:** APPROVED

For the 7 subagents disabled via settings, I assessed their domains myself (below), tagging each with its dispatch tag.

### Observations

1. **[VERIFIED] AC3d `validGenreSlug` guard is correct and load-bearing** — `ConnectScreen.tsx` derives `validGenreSlug = genreSlug && genres[genreSlug] ? genreSlug : null` and routes accent, archetype, `currentPack`, lore/rules, and `effectiveOpenGenre` through it. Evidence: the AC3d test renders with a removed-pack saved genre and no longer crashes (`getArchetypeForGenre` is gated) and opens the first live genre. Complies with No-Silent-Fallbacks (degrades visibly, not silently).
2. **[SEC] [MEDIUM, non-blocking] Unvalidated `JSON.parse(raw) as SavedConnectState`** at `ConnectScreen.tsx:~51` (typescript.md #10). **Pre-existing** — the diff only added the `catch (err)` warn; the cast is unchanged. localStorage `genre`/`world` flow into state without a runtime shape check. Real severity low (same-origin localStorage prerequisite = already compromised; single-player/small-group app). Deferred as a follow-up hardening finding, not introduced by this story.
3. **[SEC] [MEDIUM, non-blocking] `worldSlug` interpolated unvalidated into the lore href** at `ConnectScreen.tsx:~533` (`/reference/lore/${validGenreSlug}/${worldSlug}`, CWE-22 client-side). **Pre-existing for `worldSlug`** — this diff changed only the genre half (`genreSlug`→`validGenreSlug`), *hardening* the line; `worldSlug` was always interpolated. A crafted `world: "../../x"` normalizes against same-origin, but `/reference/*` is a **public** table tool (ADR-135) with no privilege boundary. Deferred: symmetric `validWorldSlug` against `currentPack.worlds` is the right follow-up.
4. **[SEC] [LOW, non-blocking] `console.warn(..., err)` may embed an input fragment** at `ConnectScreen.tsx:~52` (CWE-209). Introduced by this diff (AC3b), but the "leaked" content is the user's *own* localStorage in their *own* browser console — no cross-user/cross-origin boundary. `catch (err)` is TS-default `unknown` (not `any`), so rule #11's narrowing requirement is met. Accepted as-is.
5. **[SILENT] [VERIFIED] No new silent failures — the opposite** — the three previously-empty catches (`loadSavedState`, `saveState`, `/dev/scenes`) now `console.warn`. This is the explicit AC3b intent. Evidence: diff shows `catch {}` → `catch (err) { console.warn(...) }` ×3.
6. **[TEST] [VERIFIED] Test quality sound** — 17 tests, meaningful assertions, an App-mount wiring test (CLAUDE.md "every suite needs a wiring test"), 3 documented green regression-guards, and an honest jsdom static-proxy caveat for AC1/AC2 (no Playwright in-repo). The loadSavedState spy-target fix (instance vs `Storage.prototype`) was verified with a probe. No vacuous assertions.
7. **[EDGE] [VERIFIED] Boundary handling correct** — breakpoints land at 880/881 and 560/561 via arbitrary values; `validGenreSlug` null-path, empty-`genres` (loading) vs `genreError` (failure), and `currentPack`-null all handled. No off-by-one in the loading/error/folio three-way.
8. **[TYPE] [VERIFIED] No new type smells** — `validGenreSlug: string | null`, `showWorldsLoading: boolean`; no new `as any`, no stringly-typed API introduced. The one cast (`as SavedConnectState`) is pre-existing (see obs. 2).
9. **[DOC] [VERIFIED] Comments accurate** — the stale `lobby-folio.css` "falls back until self-hosted" note was correctly rewritten; `validGenreSlug` and `showGenreError`/`showWorldsLoading` carry accurate rationale comments. No stale/misleading docs.
10. **[SIMPLE] [VERIFIED] No over-engineering** — confirmed by the verify-phase simplify fan-out (reuse/quality/efficiency all clean) and my own read; no new prop/hook/component, reuses the existing testid-hook + Tailwind-utility conventions.

### Rule Compliance (typescript.md — [RULE] self-assessment, rule-checker disabled)

| Rule | Instances in diff | Verdict |
|------|-------------------|---------|
| #1 type-safety escapes (`as any`, `@ts-ignore`, non-null `!`) | 0 introduced | ✓ compliant |
| #4 null/undefined (`??` not `||`) | `validGenreSlug ?? firstGenreSlug`, `genreSlug ?? undefined` | ✓ compliant (correct `??`) |
| #6 React/JSX (deps, `key`, `dangerouslySetInnerHTML`) | new loading branch, no new effects/keys, no innerHTML | ✓ compliant |
| #10 input validation (`as T` on JSON.parse) | `JSON.parse as SavedConnectState` (pre-existing, untouched cast) | △ pre-existing gap (obs. 2) — non-blocking |
| #11 error handling (`catch unknown` + narrow; no swallow) | 3 catches now warn; `catch (err)` is unknown-typed | ✓ compliant (No-Silent-Fallbacks satisfied) |
| #8 test quality (no vacuous assertions) | 17 tests | ✓ compliant |

Rules #2/#3/#5/#7/#9/#12 (generics, enums, modules, async, build-config, bundle) — not materially exercised by this UI-polish diff.

### Devil's Advocate

Argue the code is broken. **First attack — the loading state never clears.** `showWorldsLoading = !genreError && genresEmpty`. If `/api/genres` resolves successfully with a real but *empty* `{}`, does the lobby spin forever? Checked: App's `fetchGenres` throws `"no genres"` on an empty response and sets `genreError=true`, so empty-success becomes the error path, not perpetual loading. Safe. **Second attack — a malicious localStorage payload.** An attacker writes `{genre:"x",world:"../../etc/passwd"}`. The Lore link href becomes `/reference/lore/<genre>/../../etc/passwd`. But the prerequisite is same-origin localStorage write access (DevTools/extension/XSS) — at which point the origin is already owned, and the navigation target is a *public* reference route (ADR-135) with no secrets behind it. No privilege escalation; this is a pre-existing, low-impact vector (obs. 3). **Third attack — reduced-motion does nothing because jsdom can't prove it.** True: AC1/AC2 are static-proxy only. But the Tailwind `motion-reduce:animate-none` / `max-[880px]:` classes are real and compile; the residual risk is a *rendering* bug a browser would show, flagged as a Delivery Finding for playtest. **Fourth attack — `validGenreSlug` breaks an in-flight genre.** When the catalogue arrives async, `genres[genreSlug]` flips from undefined to defined; `validGenreSlug` is derived per-render, so it self-corrects — no stale memo. **Fifth — the commit row stacks but the Start button overflows.** `max-[560px]:w-full` on the button plus `max-[560px]:flex-col max-[560px]:items-stretch` on the row makes it fill, not overflow. **Confused user:** sees "Gathering the worlds…" briefly on a slow link — strictly better than the old "server is down" flash. No new break surfaced beyond the pre-existing, low-severity localStorage-validation gap already deferred.

**Data flow traced:** localStorage `sidequest-connect` → `loadSavedState()` → `genreSlug`/`worldSlug` state → `validGenreSlug` (genre sanitized vs live catalogue) → accent/archetype/lore-href/Start. The genre leg is now guarded; the world leg remains pre-existingly unvalidated (deferred, non-blocking — public route, same-origin prerequisite).

**Pattern observed:** derived-sanitization-at-render (`validGenreSlug`) instead of state mutation — correct React pattern, self-correcting on async catalogue arrival. `ConnectScreen.tsx:~190`.

**Error handling:** all three lobby catches now warn (No-Silent-Fallbacks); cold-mount distinguishes loading from failure; `getArchetypeForGenre` crash eliminated.

**Handoff:** To SM (Morpheus) for finish-story.

## Workflow Tracking

**Workflow:** tdd  
**Phase:** finish  
**Phase Started:** 2026-06-04T04:53:51Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T04:05:15Z | 2026-06-04T04:07:28Z | 2m 13s |
| red | 2026-06-04T04:07:28Z | 2026-06-04T04:31:49Z | 24m 21s |
| green | 2026-06-04T04:31:49Z | 2026-06-04T04:41:40Z | 9m 51s |
| spec-check | 2026-06-04T04:41:40Z | 2026-06-04T04:43:25Z | 1m 45s |
| verify | 2026-06-04T04:43:25Z | 2026-06-04T04:46:12Z | 2m 47s |
| review | 2026-06-04T04:46:12Z | 2026-06-04T04:52:40Z | 6m 28s |
| spec-reconcile | 2026-06-04T04:52:40Z | 2026-06-04T04:53:51Z | 1m 11s |
| finish | 2026-06-04T04:53:51Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement  
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): A stale saved genre whose pack was removed **crashes the lobby**, not merely wedges the accordion open. `getArchetypeForGenre(genreSlug)` throws `Unknown genre slug` during render. Affects `sidequest-ui/src/screens/ConnectScreen.tsx` (the AC3d guard must sanitize the selected `genreSlug` against the live catalogue at the source so the archetype lookup, `currentPack`, and `effectiveOpenGenre` all self-correct — not just patch `effectiveOpenGenre`). *Found by TEA during test design.*
- **Gap** (non-blocking): `sidequest-ui` has **no Playwright/browser test harness** (`package.json` → `vitest run` + jsdom only). AC1 (breakpoints) and AC2 (reduced-motion) are runtime CSS behaviors jsdom cannot evaluate, so they are verified by static class/CSS-presence proxy only. The design handoff's "Notes for Dev" assumed a Playwright/runtime verify. Affects future e2e coverage for the lobby; behavioral verification of media-query layout/animation is not possible in-repo today. *Found by TEA during test design.*
- **Gap** (non-blocking): Setup created the session + branch but **not** the context docs (`context-epic-83.md`, `context-story-83-2.md` were absent; `pf validate context-story 83-2` exited 2). TEA authored both via `/pf-context` before RED. The `sm_setup_exit` gate resolved `ready` despite the missing context — a gate-recovery gap worth noting for process. *Found by TEA during test design.*
- **Improvement** (non-blocking): The AC4 cold-mount fix needs **no new prop** — `genreError=false` + empty `genres` is already an unambiguous "loading" signal (App sets `genreError=true` on real/empty-response failure). The fix is internal to `ConnectScreen` render branching. *Found by TEA during test design.*

### Dev (implementation)
- **Resolved** (non-blocking): The TEA-flagged stale-genre crash (`getArchetypeForGenre` throwing on a removed-pack saved genre) is fixed via `validGenreSlug` in `sidequest-ui/src/screens/ConnectScreen.tsx`. No further action. *Found/resolved by Dev during implementation.*
- **Gap** (non-blocking): AC1/AC2 ship verified by static class/CSS proxy only — confirming the TEA finding that `sidequest-ui` has no Playwright/browser harness. A runtime visual pass (881-vs-880 / 561-vs-560 layout; emulated `prefers-reduced-motion`) should happen at playtest/review. Affects future e2e coverage, not this story's correctness. *Found by Dev during implementation.*
- No upstream findings during test verification — simplify fan-out (reuse/quality/efficiency) returned clean across all 4 files. *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): Saved lobby state from `localStorage` is consumed without runtime validation — `JSON.parse(raw) as SavedConnectState` and the `worldSlug` half of the lore href are unvalidated (pre-existing; this story hardened only the genre half via `validGenreSlug`). Affects `sidequest-ui/src/screens/ConnectScreen.tsx` (add a slug-safe runtime shape check at the parse boundary and a symmetric `validWorldSlug` against `currentPack.worlds`). Low real severity (same-origin localStorage prerequisite; `/reference/*` is public per ADR-135) — a follow-up hardening story, not a 83-2 blocker. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC1/AC2 verified by static class/CSS-presence, not runtime layout/animation**
  - Spec source: docs/design/83-2-lobby-folio-followups.md, "Notes for Dev" + context-story-83-2.md AC1/AC2
  - Spec text: "Reduced-motion and breakpoint behavior are runtime-only (jsdom can't see media queries) — they need a Playwright/runtime verify."
  - Implementation: Tests assert the rendered className carries the 880/560 breakpoint and `motion-reduce:animate-none` guards (and a `--breakpoint` CSS-registration fallback), rather than driving a real viewport / `emulateMedia`.
  - Rationale: `sidequest-ui` ships no Playwright/browser harness; jsdom has no layout engine. Static-proxy is the only in-repo option and still catches the exact shipped bug (768/640 defaults; unguarded animations).
  - Severity: minor
  - Forward impact: True behavioral verification deferred to a future e2e harness (Delivery Finding). A correct fix using a registered v4 breakpoint with a non-880/560 *name* but correct px is accepted via the `--breakpoint-*: <px>` CSS check.
- **AC1 "stacked commit row" asserted via full-width Start, not the row itself**
  - Spec source: context-story-83-2.md AC1
  - Spec text: "stacked commit row + full-width Start at <=560px"
  - Implementation: Test targets the existing `lobby-start-button` (full-width @560); the commit-row `<div>` has no testid and the spec only mandated `lobby-accent-root`, so row-stacking is not directly asserted.
  - Rationale: avoid inventing test-hooks beyond the spec; full-width Start is the targetable, load-bearing half of the 560 behavior.
  - Severity: minor
  - Forward impact: row-stacking confirmed at runtime (Playwright) when a harness exists.
- **AC3b saveState catch verified at source level, not behaviorally**
  - Spec source: context-story-83-2.md AC3(b)
  - Spec text: "console.warn added to the three silent catches (/dev/scenes, loadSavedState, saveState)"
  - Implementation: /dev/scenes and loadSavedState are tested behaviorally (spy + forced failure); `saveState` is module-private and not triggerable in isolation, so it's asserted by grepping the function body for `console.warn`.
  - Rationale: saveState only runs inside the start flow, which needs a full `useStartGame` harness; source-level assertion is the proportionate proof for a one-line catch.
  - Severity: minor
  - Forward impact: none.

### Dev (implementation)
- **AC1 below-fold grid + pane divider aligned to the 880 boundary (beyond the two tested elements)**
  - Spec source: docs/design/83-2-lobby-folio-followups.md finding #1; context-story-83-2.md AC1
  - Spec text: "single-column folio + two-up index grid at <=880px ... The relevant classes are in ConnectScreen.tsx (md:grid-cols-[296px_1fr], md:grid-cols-2)"
  - Implementation: In addition to the tested folio grid + Start button, I moved the world-index pane divider (`md:border-r/md:border-b-0` → `min-[881px]:`) and the below-fold sections grid (`md:grid-cols-2` → `min-[881px]:grid-cols-2`) onto the same 880 boundary, so the whole page collapses to single-column at <=880 consistently.
  - Rationale: the design explicitly named `md:grid-cols-2` as a class to fix; leaving the divider/below-fold at md(768) would visually contradict the folio collapsing at 880 (right-border on a stacked layout). "two-up index grid at <=880" is ambiguous; I read it as the page-wide single→two-column transition aligning to 880.
  - Severity: minor
  - Forward impact: none — purely responsive layout; confirm the below-fold interpretation at runtime review.
- **AC3d guard implemented as a derived `validGenreSlug` across all presentation lookups, not only `effectiveOpenGenre`**
  - Spec source: context-story-83-2.md AC3(d)
  - Spec text: "effectiveOpenGenre guarded against a stale genre whose pack was removed"
  - Implementation: introduced `validGenreSlug` and routed accent, archetype, lore/rules links, currentPack, and effectiveOpenGenre through it (raw `genreSlug` state retained for start/save).
  - Rationale: the parked-item text said "guard effectiveOpenGenre," but the stale genre also crashes `getArchetypeForGenre` and would render a dead accent/broken links — sanitizing once at the source is the complete, single-point fix.
  - Severity: minor
  - Forward impact: none.
- **Repaired a TEA test's mock target (instance vs prototype)**
  - Spec source: TEA test `ConnectScreen.ac8.test.tsx` (loadSavedState warn)
  - Spec text: test spied `Storage.prototype.getItem` to force the catch.
  - Implementation: changed to `vi.spyOn(localStorage, "getItem")` — the test-setup localStorage polyfill defines `getItem` as an own property, so the prototype spy never intercepted (verified with a probe). Asserted behavior unchanged.
  - Rationale: false-negative in the test mechanism, not the implementation; the catch correctly warns.
  - Severity: trivial
  - Forward impact: none.

### Reviewer (audit)
- **TEA: AC1/AC2 verified by static proxy, not runtime** → ✓ ACCEPTED by Reviewer: jsdom has no layout engine and the repo ships no Playwright; static-proxy is the only in-repo option and catches the shipped 768/640 bug. Runtime pass deferred to playtest (Delivery Finding).
- **TEA: "stacked commit row" via full-width Start** → ✓ ACCEPTED by Reviewer: full-width Start is the targetable, load-bearing half; row-stack confirmed at runtime later.
- **TEA: saveState catch verified at source level** → ✓ ACCEPTED by Reviewer: saveState is module-private; source-grep is proportionate for a one-line catch.
- **Dev: below-fold grid + pane divider aligned to 880** → ✓ ACCEPTED by Reviewer: the design explicitly named `md:grid-cols-2`; page-wide 880 alignment is the consistent, correct reading.
- **Dev: AC3d guard broader than `effectiveOpenGenre` (`validGenreSlug`)** → ✓ ACCEPTED by Reviewer: the narrower guard would leave the `getArchetypeForGenre` crash; single-point sanitization is architecturally correct.
- **Dev: repaired TEA test mock target (instance vs prototype)** → ✓ ACCEPTED by Reviewer: false-negative in the mock mechanism; asserted behavior unchanged, verified with a probe.
- **UNDOCUMENTED (Reviewer-found): `worldSlug` not sanitized symmetrically with `validGenreSlug`** → ✗ FLAGGED by Reviewer (non-blocking): the lore href interpolates `worldSlug` from localStorage without a catalogue-membership check. **Pre-existing** (this diff hardened only the genre half) and out of the genre-scoped AC3d, so not a blocker — but a `validWorldSlug` follow-up is warranted. Severity: M. Logged as a Delivery Finding.

### Architect (reconcile)

Verified all in-flight deviation entries: the `### TEA (test design)` (3 entries) and `### Dev (implementation)` (3 entries) subsections each carry all 6 fields with accurate, existing spec-source paths (`docs/design/83-2-lobby-folio-followups.md`, `sprint/context/context-story-83-2.md`) and quotes that match the source. No corrections needed. AC accountability: all four ACs (AC1–AC4) are DONE — none deferred or descoped, so no deferral justifications to cross-check.

One deviation was surfaced by the Reviewer but not logged in-flight by TEA/Dev; formalized here as the definitive manifest entry:

- **`worldSlug` restored from localStorage is not sanitized against the live catalogue (asymmetric with the AC3d `validGenreSlug` guard)**
  - Spec source: sprint/context/context-story-83-2.md, AC3(d)
  - Spec text: "(d) effectiveOpenGenre guarded against a stale genre whose pack was removed."
  - Implementation: The AC3d guard was implemented as a derived `validGenreSlug` (`genreSlug && genres[genreSlug] ? genreSlug : null`) covering the genre across all presentation lookups. The sibling `worldSlug` — also restored from the `sidequest-connect` localStorage key via `JSON.parse(raw) as SavedConnectState` — receives no equivalent `currentPack.worlds` membership check before it is interpolated into the lore href `/reference/lore/${validGenreSlug}/${worldSlug}` and passed to `start()`/history.
  - Rationale: AC3d is explicitly genre-scoped; `worldSlug` validation is outside the AC. The `worldSlug` interpolation is pre-existing — this story changed only the genre half of that href (`genreSlug` → `validGenreSlug`), hardening rather than regressing the line. Reviewer rated it Medium/non-blocking: `/reference/*` is a public table tool (ADR-135) with no privilege boundary, and the attack requires same-origin localStorage write access (already a compromised origin).
  - Severity: minor (non-blocking)
  - Forward impact: A follow-up hardening story should add a runtime slug-shape check at the `JSON.parse` boundary and a symmetric `validWorldSlug` derived from `currentPack.worlds`. Already captured as a Reviewer Delivery Finding under `### Reviewer (code review)`.