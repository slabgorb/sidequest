---
story_id: "65-16"
jira_key: ""
epic: ""
workflow: "tdd"
---

# Story 65-16: 65-4 follow-ups: clear preloadedAssets on session switch + preload hardening + test tightening

## Story Details

- **ID:** 65-16
- **Jira Key:** (none — Jira not enabled)
- **Workflow:** tdd (phased: red→green→review→finish)
- **Type:** bug
- **Points:** 2
- **Repo:** sidequest-ui (React/TypeScript)
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T09:56:22Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04 | 2026-06-04T09:23:59Z | 9h 23m |
| red | 2026-06-04T09:23:59Z | 2026-06-04T09:43:39Z | 19m 40s |
| green | 2026-06-04T09:43:39Z | 2026-06-04T09:47:12Z | 3m 33s |
| review | 2026-06-04T09:47:12Z | 2026-06-04T09:56:22Z | 9m 10s |
| finish | 2026-06-04T09:56:22Z | - | - |

## Sm Assessment

Story 65-16 is a tightly-scoped 2pt UI bug follow-up to 65-4 (asset preloading). Three concrete ACs, all in `sidequest-ui`:

1. **Clear `preloadedAssets` on session leave** — `handleLeave()` in App.tsx must reset the preload state alongside its other resets, so assets from session A can't leak into session B.
2. **Harden the preload path** — extend `useAssetPreload` deps to include `slug` (re-fetch on slug change while connected, not only on the rising edge of `connected`); wire the `onError` callback at the mount site to surface preload failures.
3. **Tighten tests** — cover slug-change-while-connected, `onError` invocation on failure, url-less row dropping + console.error, and the new `handleLeave` behavior.

Self-contained to one repo, clear ACs, real cross-session isolation bug worth a regression test — good fit for tdd. Base branch is `develop` (sidequest-ui), branch created. No Jira (integration disabled). No blocking PRs. Routing to TEA for RED.

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes
**Reason:** Three concrete behavioral ACs (cross-session isolation + preload hardening); a real cross-session leak bug worth a permanent regression test.

**Test Files:**
- `sidequest-ui/src/hooks/__tests__/useAssetPreload.test.ts` — extended: new describe block `useAssetPreload — 65-16 slug-change re-preload (AC2a)` (3 tests).
- `sidequest-ui/src/__tests__/asset-preload-app-wiring-65-16.test.tsx` — new file: AC1 (leave clears) + AC2b (App onError → banner) (3 tests).

**Tests Written:** 6 new tests covering 3 ACs (3 RED + 3 passing guards/controls).
**Status:** RED (3 failing, ready for Dev). 11 of 14 pass (8 pre-existing 65-2/65-4 hook tests + 2 AC2a guards + 1 AC2b success-control).

**The 3 RED tests (verified to fail for the right reason, not infra):**
| AC | Test | Failure (verbatim) |
|----|------|--------------------|
| AC2a | `re-preploads for the NEW slug when the slug changes while staying connected` | `expected "vi.fn()" to be called 2 times, but got 1 times` — hook keys only on the `connected` rising edge; a slug change while connected never re-fires. |
| AC1 | `does not leak the prior session's backfill after leave + re-entry` | `expected [ …(2) ] to not include 'https://cdn.slabgorb.com/…'` — `handleLeave` resets ~two dozen fields but not `preloadedAssets`, so the prior session's backfill renders in the re-entered gallery. |
| AC2b | `shows the transient-error banner when the asset ledger preload fails` | `Unable to find an element by: [data-testid="transient-error-banner"]` — App mounts `useAssetPreload` with no `onError`, so a failed preload is logged but never surfaced. |

**Implementation pointers for Dev (Naomi):**
- AC1: add `setPreloadedAssets([])` to `handleLeave` in `App.tsx:1611` (alongside the other resets).
- AC2a: `useAssetPreload` must re-preload when `slug` changes while `connected` — track last-preloaded slug, not just the `connected` rising-edge ref (`useAssetPreload.ts:46-85`). The disconnected-slug-change guard test pins that it must NOT fire when `connected === false`.
- AC2b: pass an `onError` to the `useAssetPreload` mount site (`App.tsx:609`) that calls `setTransientError(...)` (the Story 71-3 surface, testid `transient-error-banner`).

### Rule Coverage

| Rule (typescript.md) | Test(s) | Status |
|------|---------|--------|
| #6 React/JSX — `useEffect` dependency correctness | `re-preloads for the NEW slug…` + `does NOT re-preload on a slug change while DISCONNECTED` | failing / passing-guard — pins that `slug` must drive the effect without becoming an always-fire effect |
| #8 Test quality — meaningful assertions, no `as any` | self-check (Phase C) over all 6 new tests | pass — every test has a non-vacuous assertion; positive/negative pairs on AC1 and AC2b |
| #11 Error handling — failures surface, not swallowed | `shows the transient-error banner when the asset ledger preload fails` | failing — enforces the onError hand-off reaches a user surface |

**Rules checked:** 3 of 13 lang-review rules are directly applicable to these tests (the rest concern source patterns Dev will introduce in GREEN — e.g. `??` vs `||`, exhaustiveness — and are out of scope for test authoring).
**Self-check:** 0 vacuous tests found.

**Handoff:** To Dev (Naomi) for implementation.

### TEA (test design) — Delivery Findings

- No upstream findings during test design.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/hooks/useAssetPreload.ts` — AC2a: added a `lastPreloadedSlug` ref; the effect now fires on the `connected` rising edge OR when `slug` changes while connected, and returns early when `!connected` (the disconnected-slug-change guard).
- `sidequest-ui/src/App.tsx` — AC1: `handleLeave` now calls `setPreloadedAssets([])` alongside the other resets. AC2b: added a stable `handlePreloadError` callback (`useCallback`, sets `transientError`) and passed it as `onError` to the `useAssetPreload` mount site.

**Tests:** 14/14 story tests passing (GREEN). Full UI suite: 1815/1815 passing (189 files) — no regressions, incl. the 65-2/65-4 preload tests.
**Branch:** `feat/65-16-clear-preloaded-assets-session-switch` (pushed).

**Self-review:**
- Wiring: `onError` is now reached from the production mount site; `setPreloadedAssets([])` is in the live `handleLeave`; the slug-change branch is exercised by the App-level integration test. All three changes have non-test consumers.
- Lint: `eslint` clean on changed files (2 pre-existing `exhaustive-deps` warnings at App.tsx:1368/1974 are unrelated to this change).
- ACs: all three met; error handling (AC2b) implemented per the 71-3 transient-error surface.

**Handoff:** To Reviewer (Chrisjen) for code review.

### Dev (implementation) — Delivery Findings

- No upstream findings during implementation.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (lint clean, typecheck clean, 1815/1815 green) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 6 (1 high, 2 med, 3 low) | confirmed 1, dismissed 2, deferred 3 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 (2 med, 1 low) | confirmed 0, dismissed 1, deferred 2 |
| 4 | reviewer-test-analyzer | Yes | findings | 6 (4 med, 2 low) | confirmed 0, dismissed 1, deferred 5 |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 (low) | confirmed 0, deferred 1 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 1 confirmed (fixed inline), 4 dismissed (with rationale), 11 deferred (non-blocking follow-ups / delivery findings)

## Reviewer Assessment

**Verdict:** APPROVED (one HIGH finding fixed inline at the user's direction during review)

The three ACs are correctly implemented and tested. Adversarial review surfaced one genuine cross-session leak — introduced by the AC2b onError wiring — which I **fixed inline** (Bossmang directed: "fix inline now if it is a small fix"). It was a one-line `setTransientError(null)` in `handleLeave` plus a regression test. Fix verified RED→GREEN; full suite 1816/1816.

### Observations

1. `[EDGE][HIGH → FIXED]` `handleLeave` cleared ~two dozen per-session fields but not `transientError` (App.tsx:1619). With AC2b now routing a failed preload to that banner (App.tsx:609 `handlePreloadError`), the "Couldn't load this session's saved images" strip survived the leave, rendered in the lobby (top-level banner at App.tsx:2200), and bled into the next session — the exact cross-session leak this story exists to kill, and not caught by the original AC1 test (its first preload succeeded, so no banner pre-leave). **Fixed:** `setTransientError(null)` added to `handleLeave`; regression test `clears the failed-preload banner on leave` added. Evidence: pre-fix the test failed with `expected document not to contain element, found <div data-testid="transient-error-banner">`; post-fix green.
2. `[VERIFIED]` `handleLeave` clears `preloadedAssets` — App.tsx:1627 `setPreloadedAssets([])`. AC1 core fix present and exercised by the leave+re-entry integration test. Complies with the story's cross-session-isolation intent.
3. `[VERIFIED]` `cancelled`-flag correctness on rapid slug churn (A→B→A) — useAssetPreload.ts:69-97. **Challenged** edge-hunter's medium "double-onAssets race": React runs effect cleanup **synchronously during the commit phase**, before control yields to the event loop where an awaited `fetch` can resolve. Every superseded effect's `cancelled` is therefore `true` before its fetch settles, so only the latest closure ever calls `onAssets`. No double-feed. Dismissed both medium race findings on this basis.
4. `[SEC][LOW → deferred]` `handlePreloadError` interpolates `err.message` without the `sanitizeErrorMessage` applied on the parallel server-error path (App.tsx:1226). Safe today — the message is hook-constructed (`asset preload failed: <status>`) or a browser-generated `TypeError`, never server-body text — but inconsistent. `[VERIFIED]` no XSS: banner renders `{transientError}` as a React text node (App.tsx:2206), auto-escaped; no `dangerouslySetInnerHTML`.
5. `[SILENT][LOW → deferred]` failed-preload non-retry: `lastPreloadedSlug.current` is stamped before the fetch (useAssetPreload.ts:67), so a same-slug failure won't auto-retry without a reconnect or slug change. The transient banner + console.error keep it loud, and a reconnect rising-edge does retry. Out of AC scope; deferred as a non-blocking improvement.
6. `[TEST][MED → deferred]` AC1 re-entry test asserts absence (`not.toContain`) without first asserting the re-entry preload fired (fetch called 2×); hardening would make the negative a consequence of an observed event. The test was verified RED→GREEN so it does pin the clear; the hardening is a nice-to-have.
7. `[SILENT]/[DISMISS]` url-less ledger rows dropped silently in `handlePreloadAssets` — **pre-existing** code (App.tsx:588-604) NOT touched by this diff; 65-4 already tests the drop + `console.error`. Out of scope.
8. `[DOC]` N/A — reviewer-comment-analyzer disabled via settings. (Spot-check by author: the rewritten hook docstring and the new inline comments accurately describe the slug-change behavior.)
9. `[TYPE]` N/A — reviewer-type-design disabled. (Spot-check: `onError?: (error: unknown) => void` and `err instanceof Error` narrowing comply with typescript-review #11; `slug ?? null` is correct nullish handling per #4.)
10. `[SIMPLE]` N/A — reviewer-simplifier disabled. (The `lastPreloadedSlug` ref is the minimal mechanism for slug-aware re-fire; no over-engineering observed.)
11. `[RULE]` N/A — reviewer-rule-checker disabled. See Rule Compliance below for the manual pass.

### Rule Compliance (typescript.md manual pass)

- **#4 Null/undefined:** `slug ?? null` at the mount site (App.tsx:610) is correct — `slug` from `useParams` is `string | undefined`; `??` (not `||`) preserves intent. Hook's `!slug` guard correctly treats empty string as absent. **Compliant.**
- **#6 React/JSX hook deps:** `useAssetPreload`'s effect deps `[slug, connected, onAssets, onError]` are complete; `handlePreloadError` is `useCallback(..., [])` with a stable setter, so it doesn't refire the effect. `handleLeave` adds `setTransientError` (stable setter, no dep change needed). **Compliant** (the 2 pre-existing exhaustive-deps warnings at 1368/1974 are unrelated to this diff).
- **#11 Error handling:** hook `catch (err)` is `unknown`; `handlePreloadError(err: unknown)` narrows with `instanceof Error`. Failures surface via `onError` + `console.error`. **Compliant.**
- **#1 Type escapes:** `resp.json() as SessionAsset[]` is an unvalidated cast but is **pre-existing/unchanged** — no new escape introduced.

### Devil's Advocate

Suppose this code is broken. The most damaging path is the one I fixed: a player on a flaky network (or mid-deploy, when the asset ledger 503s are common) sees the failed-preload banner, gives up on that session, clicks Leave, joins a *different* game — and the new game greets them with "Couldn't load this session's saved images," a lie about a session whose images loaded fine. They distrust the new session and the app. That is a real, repeatable defect, and it is precisely the cross-session bleed the story sets out to eliminate; shipping it inside *this* story would have been self-defeating. Beyond that: a confused user rapidly bouncing between two history entries (A→B→A→B) with an intermittent ledger triggers a preload per switch — each failure re-raises the banner, but I verified the hook re-fires per distinct slug and the `cancelled` flag suppresses stale feeds, so no wrong-session images render; the only residue is the banner, now cleared on leave. A stressed filesystem/CDN returning a 200 with url-less rows is dropped silently — but that is pre-existing 65-4 behavior, loudly `console.error`'d, and outside this diff. A malicious server can't XSS via the banner (React text-escaped) and can't inject the fetch URL (slug stays `encodeURIComponent`-wrapped on the new path). The residual real-but-narrow weakness is the no-auto-retry-on-failure (a transient 503 leaves a session without backfill until a reconnect), which I've logged as a non-blocking follow-up rather than block a 2-pt story on an edge the ACs never claimed.

**Data flow traced:** failed `GET /api/sessions/{slug}/assets` → hook `onError?(Error)` → `handlePreloadError` → `setTransientError(text)` → `{transientError}` banner (React-escaped text node). On `handleLeave` → `setTransientError(null)` → banner cleared before lobby/next session. Safe.

**Pattern observed:** per-session state reset centralized in `handleLeave` (App.tsx:1619) — the fix correctly extends the existing pattern rather than inventing a new teardown path.

**Error handling:** failures are loud (console.error unconditional + onError → banner); no swallowed paths introduced.

**Handoff:** To SM for finish-story.

### Reviewer (code review) — Delivery Findings

- **Improvement** (non-blocking): `handlePreloadError` should route `err.message` through `sanitizeErrorMessage` for consistency with the server-error path. Affects `sidequest-ui/src/App.tsx` (~line 609; apply `sanitizeErrorMessage` to the detail string). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): failed preload does not auto-retry on a same-slug re-render (`lastPreloadedSlug` stamped pre-fetch). Affects `sidequest-ui/src/hooks/useAssetPreload.ts` (reset `lastPreloadedSlug.current = null` on the failure paths to allow retry). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): slug-change re-preload that itself fails leaves the prior session's `preloadedAssets` visible until a live image arrives (modal-nav path; AC1's clear is leave-only). Affects `sidequest-ui/src/App.tsx` / `useAssetPreload.ts` (consider clearing on slug change). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): test hardening — assert the AC1 re-entry preload fired (fetch called 2×) before the negative gallery assertion; add slug-change-failure `onError` and explicit A→B→A coverage. Affects `sidequest-ui/src/__tests__/asset-preload-app-wiring-65-16.test.tsx` and `useAssetPreload.test.ts`. *Found by Reviewer during code review.*

## Delivery Findings

No upstream findings.

## Design Deviations

### Reviewer (audit)
- **TEA: AC1 re-entry uses the same slug** → ✓ ACCEPTED by Reviewer: sound — same-slug re-entry reproduces the identical App-state leak while dodging the NamePrompt identity gate; the fix is slug-agnostic. Test-analyzer's suggestion to also assert the re-entry preload fired is logged as a non-blocking hardening.
- **Dev: No deviations from spec** → ✓ ACCEPTED by Reviewer: confirmed — implementation matches the ACs and TEA's pointers; the one gap (transientError clear) was an omission in the same teardown function, now fixed inline, not a spec deviation.

### Dev (implementation)
- No deviations from spec.

### TEA (test design)
- **AC1 re-entry uses the same slug rather than a different one**
  - Spec source: context-story-65-16.md, AC1
  - Spec text: "the old session's preloaded assets leak into the new one… when a player leaves the session or switches to a different session"
  - Implementation: The AC1 integration test leaves and re-enters the SAME slug (ledger serves rows on the first preload, 500 on re-entry) instead of switching to a different slug.
  - Rationale: A different-slug re-entry trips the slug-mode NamePrompt identity-trust gate (`App.tsx:2123`), which would require driving a name-confirmation sub-flow and made the test brittle (timeouts). Same-slug re-entry stays identity-trusted via journey history and reproduces the identical leak mechanism (un-cleared App-level `preloadedAssets`), isolating exactly the `handleLeave` clear. The leak is slug-agnostic — it is App state, not session-keyed.
  - Severity: minor
  - Forward impact: none — the production fix (`setPreloadedAssets([])` in `handleLeave`) is identical for both re-entry paths.