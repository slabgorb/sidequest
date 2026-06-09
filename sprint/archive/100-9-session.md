---
story_id: "100-9"
jira_key: ""
epic: "100"
workflow: "tdd"
---
# Story 100-9: Phase 2 — Session-free theme injector (CSS-var mechanism fed from projection JSON, not WS theme_css; C3)

## Story Details
- **ID:** 100-9
- **Jira Key:** (none — SideQuest does not use Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-ui

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-09 10:17:17

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-06-09 10:17:17 | - | - |

## Delivery Findings

This story builds on two already-merged dependencies:
- **100-7** (server, completed 2026-06-09): projection JSON now carries top-level `doc["theme"]` = flat CSS-var token dict (`{"--var":"value"}`)
- **100-8** (ui, completed 2026-06-09): session-free `/reference/*` React shell (ReferenceLorePage/ReferenceRulesPage via useReferenceProjection hook)

**Concern C3 (this story):** A SESSION-FREE theme injector — a CSS-var mechanism that applies `doc["theme"]` from projection JSON to the document, INSTEAD of the in-game WebSocket `theme_css` channel. Must work on session-free `/reference/*` pages (no WebSocket).

### Known Develop Baseline Noise (NOT IN SCOPE — Epic 97-7/97-8)
- `client-build` RED on develop from 73-4/97-3 `ConfrontationOverlay.beatimpact.test.tsx` (BeatEffect union)
- `lobby-start-ws-open.test.tsx` is flaky (5s timeout)
- TEA/Dev/Reviewer: baseline-diff these at the start of green; do not chase them here.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- **Gap** (non-blocking): `ReferenceRulesPage` is not wired to `useThemeTokens` — it consumes `useReferenceProjection<RulesProjection>` but never applies `data.theme`, so session-free `/reference/rules/*` pages render unthemed even though `RulesProjection.theme` exists in the type. No leak/correctness bug (Lore→Rules navigation cleanly drops Lore's vars on unmount). Affects `src/screens/reference/ReferenceRulesPage.tsx` (add the same one-line `useThemeTokens(data?.theme)` to complete `/reference/*` theming). *Found by Reviewer during code review.*

### TEA (test design) — RED complete 2026-06-09

**Pinned contract** for the session-free theme injector (Concern C3):

- **Name / kind:** `useThemeTokens` hook (mirror of the in-game `useGenreTheme`).
- **File (production, for Dev):** `src/screens/reference/useThemeTokens.ts`
- **Signature:**
  ```ts
  export function useThemeTokens(
    theme: ReferenceTheme | undefined,   // doc["theme"] flat {"--var": value} dict
    target?: HTMLElement,                // default: document.documentElement (:root)
  ): void
  ```
- **Mechanism:** `target.style.setProperty(name, value)` per `--var` (same var-application
  mechanism as `useGenreTheme`), but the SOURCE is the REST projection JSON's `theme`
  field — NOT the WS `theme_css` SESSION_EVENT. No `<style>` tag, no `data-genre`
  attribute, no WebSocket, no session.
- **Application scope:** `document.documentElement` by default so reference CSS reads
  `--primary` etc. off `:root`; an explicit `target` element is honored (scoping
  contract pinned by test).
- **Cleanup semantics (anti-leak):**
  - On unmount → every var the hook set is `removeProperty`'d (no leak back into lobby /
    in-game theme).
  - On theme change (pack/route switch) → vars present in the PREVIOUS dict but absent
    from the new dict are removed; shared keys are updated. No stale cross-pack var
    survives.
  - `undefined` / empty theme → safe no-op (theme is optional on the projection).

**Test files (RED, committed):**
- `src/screens/reference/__tests__/useThemeTokens.test.tsx` — 6 behavior tests
  (vars land, no-WS, cleanup-on-unmount, pack-switch leak, undefined no-op, custom-target scope).
  Fails: module-not-found (`useThemeTokens` not yet created) — correct RED.
- `src/screens/reference/__tests__/ReferenceLorePage.theme.test.tsx` — 2 WIRING tests
  (theme from fetched REST projection lands on `:root` with NO WebSocket; removed on
  page unmount). Dev wires `useThemeTokens(data?.theme)` into `ReferenceLorePage`.
  Fails: page does not apply theme yet — correct RED.

**Baseline-diff:** failures are isolated to the two new files; NOT the known develop noise
(97-7 ConfrontationOverlay build error; 97-8 lobby-ws flake).

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Removed an unused `@ts-expect-error` directive in TEA's RED test**
  - Spec source: TEA RED commit c25f90f, `src/screens/reference/__tests__/useThemeTokens.test.tsx` line 67
  - Spec text: `// @ts-expect-error — replace the constructor with a tripwire for the test.` above `globalThis.WebSocket = function () {...} as unknown as typeof WebSocket;`
  - Implementation: Replaced the directive with a plain comment (and avoided the literal `@ts-expect-error` token in the comment text, which TypeScript also parses as a directive). The `as unknown as typeof WebSocket` cast already makes the assignment type-valid, so the directive was unused.
  - Rationale: `tsc -b` (the `client-build` gate) fails on an unused `@ts-expect-error` (TS2578). Vitest tolerated it but the build did not. Minimal change to keep the build gate's only remaining errors the documented 97-7/73-4/97-3 `ConfrontationOverlay` baseline. Test behavior (asserting no WebSocket is constructed) is unchanged.
  - Severity: trivial
  - Forward impact: none — comment-only change to a test file.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/screens/reference/useThemeTokens.ts` (new) — session-free CSS-var injector hook; `setProperty` per `--var` from the projection `theme` dict onto a target (default `:root`); `useEffect` cleanup removes exactly the vars it set, so unmount and pack/theme switch both drop stale vars (no cross-pack leak); `undefined`/empty theme is a no-op.
- `src/screens/reference/ReferenceLorePage.tsx` — wired `useThemeTokens(data?.theme)` (the production consumer / wiring point).
- `src/screens/reference/__tests__/useThemeTokens.test.tsx` — removed an unused `@ts-expect-error` directive that broke `tsc -b` (see deviation above).

**Tests:** 8/8 passing (GREEN) — 6 behavior + 2 wiring. Full suite: 1944 passed, 1 failed (the pre-existing 97-8 `lobby-start-ws-open.test.tsx` 5s flake — documented baseline, not mine).
**Build (`tsc -b`):** only the 5 documented 97-7/73-4/97-3 `ConfrontationOverlay.beatimpact.test.tsx` BeatEffect errors remain (develop baseline). Zero new build errors from this diff.
**Lint:** 0 errors, 1 pre-existing `App.tsx` warning (not mine).
**Branch:** feat/100-9-session-free-theme-injector (pushed)

**Handoff:** To review.

## Reviewer Assessment

**Verdict:** APPROVED
**Data flow traced:** REST `/reference/api/lore/:pack/:world` → `useReferenceProjection` (plain `fetch`, no WS) → `data.theme` (flat `{"--var":"value"}` dict) → `useThemeTokens` → `el.style.setProperty` on `:root`. Safe because the projection JSON is the sole feed — no WebSocket `theme_css` channel, no GameStateProvider, no auth.
**Session-free invariant:** VERIFIED. Wiring test stubs `WebSocket` globally and asserts `wsCtor` never called while content renders + vars land — non-vacuous (fetch stubbed, content asserted first, then `:root` vars).
**Vars actually applied:** VERIFIED. Tests assert `document.documentElement.style.getPropertyValue("--primary")` equals the exact hex, not merely that `setProperty` was called.
**Cleanup / no cross-pack leak (load-bearing):** VERIFIED. Effect returns a cleanup removing exactly the vars it set; deps `[theme, target]` run cleanup-then-setup on a pack switch. Cross-pack test (PACK_A → packB lacking `--accent`) asserts `getPropertyValue("--accent") === ""` — proves the stale var is removed, not left on `:root`. `useReferenceProjection` returns a stable `settled.data` reference per pack (setState only on fetch settle), so no per-render churn; a route-change loading frame clears `theme→undefined` which fires cleanup before the new pack applies. No leak in rerender or production path.
**@ts-expect-error removal:** VERIFIED pure compiler-directive cleanup — `expect(wsConstructed).toBe(false)` and the `as unknown as typeof WebSocket` cast are unchanged; removing the now-unused directive is required (TS2578 fails `tsc -b`).
**Test quality:** Testing-Library (`renderHook`, `render`/`waitFor`), no snapshots, no implementation coupling — asserts DOM state. 8/8 story tests pass.
**Gates (baseline-diffed via merge-base; develop NOT checked out):**
- Lint: 0 errors, 1 pre-existing `App.tsx` warning (not in diff).
- Build `tsc -b`: 5 errors, ALL in `ConfrontationOverlay.beatimpact.test.tsx` (97-7/73-4/97-3 `BeatEffect` baseline) — NOT in the 100-9 diff. Zero new.
- Test: 1944 passed / 1 failed; the failure is `lobby-start-ws-open.test.tsx` (97-8 flake) — NOT in the 100-9 diff. Zero new.
**Deviation audit:** Dev's `@ts-expect-error` removal — ACCEPTED (pure directive cleanup, assertion unchanged, required for the build gate).
**Observations:** Clean additive diff (+293, 4 files). Mechanism is generic/reusable and proven wired on Lore. One non-blocking gap: Rules page not yet wired (see Delivery Findings).

**Handoff:** Merge PR #360 → SM finish.
