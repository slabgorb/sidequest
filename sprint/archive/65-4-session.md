---
story_id: "65-4"
jira_key: null
epic: "65"
workflow: "tdd"
---
# Story 65-4: Mount useAssetPreload in App + ImageBus preload feed (AC5 follow-up from 65-2)

## Story Details
- **ID:** 65-4
- **Jira Key:** null
- **Workflow:** tdd
- **Stack Parent:** none
- **Branch:** feat/65-4-mount-useassetpreload-imagebus-feed

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T08:21:36Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T07:34:42.639897Z | 2026-06-04T07:43:37Z | 8m 54s |
| red | 2026-06-04T07:43:37Z | 2026-06-04T07:54:14Z | 10m 37s |
| green | 2026-06-04T07:54:14Z | 2026-06-04T08:04:30Z | 10m 16s |
| spec-check | 2026-06-04T08:04:30Z | 2026-06-04T08:06:22Z | 1m 52s |
| verify | 2026-06-04T08:06:22Z | 2026-06-04T08:11:47Z | 5m 25s |
| review | 2026-06-04T08:11:47Z | 2026-06-04T08:20:08Z | 8m 21s |
| spec-reconcile | 2026-06-04T08:20:08Z | 2026-06-04T08:21:36Z | 1m 28s |
| finish | 2026-06-04T08:21:36Z | - | - |

## Sm Assessment

**Disposition:** Ready for RED. Story is fully scoped — the AC5 app-wiring follow-up the
Doctor split out of 65-2 (2026-05-27). Backend (ledger → REST → render-write with OTEL)
and the `useAssetPreload` hook already shipped and merged in 65-2; this story has a single
repo (`sidequest-ui`) and a single job: give the hook a production consumer + a wiring test.

**Technical approach for TEA/Dev:**
- **Mount** `useAssetPreload` in `AppInner` (the WebSocket-owning level it already
  documents), with router `slug`, local `connected`, and a stable `useCallback` `onAssets`.
- **AC2 feed mechanism is an OPEN design decision** (frame, don't pre-decide): synthetic
  IMAGE messages into `messages` (reuse-honest, but must engineer out render_id collision,
  reconnect-purge loss, cross-consumer pollution, and index-vs-turn ordering) **vs.** a
  second pure `preloadedAssets` input on `ImageBusProvider` (purge-immune, no pollution,
  but changes the 65-2-frozen contract signature — needs Architect sign-off). Architect
  (context creation) leans reuse-first to synthetic-messages *with its costs paid
  explicitly*; Approach 2 is the cleaner seam if RED shows the purge/pollution edges fragile.
- **Reconnect-ordering hazard** is the sharp edge: the rising-edge fetch can fire before the
  `ready` SESSION_EVENT purges `messages`; synthetic messages injected pre-purge are
  silently deleted (No-Silent-Fallbacks by omission). Approach 1 must inject post-`ready`;
  Approach 2 is immune.
- **Mandatory wiring test** (AC3) closes the explicit 65-2 Dev finding "no app-integration/
  wiring test" — App-level render asserting the encoded fetch fires AND a preloaded URL
  renders through `useImageBus()`. Behavior only, no source grep.
- **AC4** folds in the 65-2 review reminders: `encodeURIComponent(slug)` + an `onError`
  callback on the hook.

**No-Silent-Fallbacks gate:** a preload row with no `url` is a server-contract violation —
loud-fail at the mapping boundary, never silently drop into the gallery.

**Wiring gate (CLAUDE.md):** RED must include the App-level integration test above — unit
coverage of the hook alone is exactly the half-wired state 65-2 left behind.

**Risks:** single-repo, no backend/daemon change, no blockers (65-2 merged). The only real
risk is the AC2 mechanism choice and its reconnect-ordering interaction — both surfaced and
dispositioned in the context for RED.

**Context:** `sprint/context/context-story-65-4.md` (validated) — authored during setup
recovery after sm-setup omitted it (known sm-setup context gap).

## Delivery Findings

This story implements the AC5 app-wiring that was deliberately split out of 65-2. Story 65-2 delivered the backend asset ledger (Postgres asset_ledger table → PgAssetLedgerStore → PgSaveRepository → GET /api/sessions/{slug}/assets → render-path write with OTEL) AND the `useAssetPreload` hook (sidequest-ui/src/hooks/useAssetPreload.ts) — but the hook has NO production consumer.

Key technical question (AC2): ImageBusProvider is a PURE REDUCER over a `messages` array (Architect constraint from 65-2). Feeding preloaded URLs needs a design decision — synthetic IMAGE messages vs. a new ImageBus input seam. This design decision belongs to Architect/Dev; flag it in code review.

Upstream findings:
- The 65-2 hook implementation exists at sidequest-ui/src/hooks/useAssetPreload.ts with unit tests
- Backend contract is live: GET /api/sessions/{slug}/assets returns array of {r2_key, asset_type, entity_ref, created_turn, url} rows
- AC4 Reviewer reminders: add `encodeURIComponent(slug)` to fetch URL and `onError` callback to hook

No upstream findings blocking RED phase.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Question** (non-blocking): App's `connected` state (App.tsx:1822) is set once at slug-connect success and does NOT toggle on a mid-session WebSocket drop/reopen (that is `readyState`/`isReconnecting`). The hook's docstring claims it fires on "initial connect OR reconnect", but if Dev passes App's coarse `connected`, the preload fires once per resume, not on every socket reopen. Dev must decide the firing signal (coarse `connected` vs `readyState===OPEN` rising edge). Affects `sidequest-ui/src/App.tsx` (mount site) and possibly `useAssetPreload.ts` (firing contract). *Found by TEA during test design.*
- **Improvement** (non-blocking): The reconnect-ordering hazard is now pinned WITHOUT a flaky WS-drop — the resume path itself exercises it. `bootResume` does connect→`ready`, and that `ready` triggers the purge (`isReconnect = sessionPhaseRef.current !== "game"` is true on resume, App.tsx:707). So `feeds prior-turn CDN URLs ... surviving the resume purge` deterministically reproduces "synthetic inject lands pre-purge then gets wiped". Dev: inject post-`ready` (Approach 1) or use a purge-immune second input (Approach 2). Affects `sidequest-ui/src/App.tsx`. *Found by TEA during test design.*
- **Improvement** (non-blocking): Both the cross-source URL dedupe (`dedupes a preloaded asset against a live IMAGE`) and the turn-based ordering (`orders backfilled assets behind live`) require `ImageBusProvider` reducer changes REGARDLESS of feed mechanism — the current reducer dedupes only by `render_id` and sorts by message index. The context's "Approach 1 = zero ImageBus change" pro therefore does not fully hold; Dev should expect to touch the reducer for ordering/dedupe even under synthetic-messages. Affects `sidequest-ui/src/providers/ImageBusProvider.tsx`. *Found by TEA during test design.*
- **Improvement** (non-blocking): The `invokes onError when the fetch itself rejects` test produces an unhandled rejection in RED because the hook's async IIFE has no try/catch (`useAssetPreload.ts:47`). This is correct RED signal; Dev's AC4 try/catch + `onError` closes both the assertion and the unhandled rejection. Affects `sidequest-ui/src/hooks/useAssetPreload.ts`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The 65-2-frozen "pure reducer over `messages`" ImageBus contract is now extended to "pure over `(messages, preloadedAssets)`" — `ImageBusProvider` gained an optional `preloadedAssets` prop. This is the contract-signature change the Architect flagged as needing sign-off; it is a *second pure input*, not a side effect (the reducer stays a pure `useMemo`). Reviewer should confirm the extension is acceptable. Affects `sidequest-ui/src/providers/ImageBusProvider.tsx`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): Backfill ordering uses a sentinel timestamp `created_turn - 1_000_000` to force preloaded assets older than any live message-indexed entry (index ≥ 0). This is robust for any realistic session (message counts are far under 1e6) but would collide if a single session ever exceeded ~1,000,000 messages. Affects `sidequest-ui/src/providers/ImageBusProvider.tsx`. *Found by Dev during implementation.*
- **Question** (non-blocking): The hook keys on App's coarse `connected` (fires once per resume), resolving TEA's firing-signal Question. A mid-session WebSocket drop/reopen without a full resume will NOT re-preload. Correct for this AC (resume rehydration); if a future story needs preload-on-every-socket-reopen, key the hook on the `readyState===OPEN` rising edge. Affects `sidequest-ui/src/App.tsx`. *Found by Dev during implementation.*

## Design Deviations

None at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC2 tests assert at the `useImageBus()` boundary, not the feed mechanism**
  - Spec source: context-story-65-4.md, AC2 (Technical Guardrails — "feed mechanism is OPEN")
  - Spec text: "How should the `SessionAsset[]` rows from `onAssets` reach the pure-reducer ImageBus? ... synthetic IMAGE messages ... vs. a second pure input ... RED/Dev decides"
  - Implementation: every AC2 test reads the observable gallery output (`useImageBus()` URLs serialized by the GameBoard stub) rather than asserting synthetic messages OR a `preloadedAssets` prop directly. Tests hold for either mechanism.
  - Rationale: the mechanism is an explicit open Dev decision; pinning it in tests would pre-empt that decision and force a rewrite if Dev picks the other approach.
  - Severity: minor
  - Forward impact: if Dev chooses Approach 2 (second pure input), no test change needed; if Approach 1 (synthetic messages), the ordering + dedupe tests force the reducer changes the context flagged ("zero ImageBus change" pro erodes).
- **"No slug → no fetch" wiring guard is non-discriminating in RED (vacuous pass)**
  - Spec source: context-story-65-4.md, AC3 ("Negative wiring assertion: with no `slug`, `fetch` is not called")
  - Spec text: "guards against an always-on mount"
  - Implementation: `does NOT fetch the asset ledger when there is no session slug` PASSES in RED because the hook is unmounted (endpoint never hit on any route). It only becomes discriminating after Dev mounts the hook and gates it on `slug`.
  - Rationale: kept deliberately — it is a meaningful GREEN guard against a mount that fires without a session; a RED-only failure is not required for every assertion. Same disposition as 65-2's vacuous-in-RED guards.
  - Severity: trivial
  - Forward impact: remains a valid guard post-GREEN.
- **AC4 `onError` tests pass a prop absent from the current `UseAssetPreloadArgs` type**
  - Spec source: context-story-65-4.md, AC4 ("`UseAssetPreloadArgs` gains an `onError` callback")
  - Spec text: "an `onError` callback on `UseAssetPreloadArgs` invoked on `!resp.ok` (and on a thrown fetch)"
  - Implementation: the two onError tests call `useAssetPreload({ slug, connected, onAssets, onError })`. `onError` is not yet on the type, so the test is also a RED *contract* assertion (a type error today). It runs under vitest (esbuild transpile, no typecheck) and fails on the runtime assertion (`onError` never called).
  - Rationale: TDD — the test expresses the desired contract; Dev adds `onError?` to the interface + impl to make it both compile and pass. No `as any`/cast used (typescript-review #8 respected).
  - Severity: minor
  - Forward impact: Dev must extend the interface and the catch path; the RED type error resolves alongside the runtime assertion.

### Dev (implementation)
- **AC2 feed mechanism: chose Approach 2 (second pure input), not Approach 1 (synthetic messages)**
  - Spec source: context-story-65-4.md, AC2 (Technical Guardrails — "feed mechanism is OPEN ... RED/Dev decides")
  - Spec text: "synthetic IMAGE messages ... vs. a second pure input ... Architect's reuse-first lean is Approach 1 ... Approach 2 is the cleaner seam if the RED tests show the pollution/purge interactions are fragile."
  - Implementation: added a `preloadedAssets?: SessionAsset[]` prop to `ImageBusProvider`; the `useMemo` now reduces over `(messages, preloadedAssets)` with a Pass-3 projection (URL dedupe vs live, turn-based ordering). App holds `preloadedAssets` state; `useAssetPreload.onAssets` sets it.
  - Rationale: the RED suite pins purge-survival, cross-source URL dedupe, AND turn-based ordering. Approach 1 would need post-`ready` re-injection, a synthetic render_id namespace, a reducer sort key, AND guards for four other `messages` consumers — the exact fragility the context names. Approach 2 makes preload purge-immune for free (separate state) and centralizes dedupe+ordering in one reducer pass. A useMemo over two inputs is still a pure reducer.
  - Severity: major (extends the 65-2-frozen ImageBus contract signature)
  - Forward impact: `ImageBusProvider` gains one optional prop; the "pure reducer over `messages`" freeze becomes "pure over `(messages, preloadedAssets)`". Flagged for Reviewer in Delivery Findings.
- **Hook firing signal: coarse App `connected`, not a per-socket reconnect edge**
  - Spec source: session Delivery Findings → TEA (test design) Question
  - Spec text: "Dev must decide the firing signal (coarse `connected` vs `readyState===OPEN` rising edge)."
  - Implementation: `useAssetPreload({ slug: slug ?? null, connected, ... })` — passes App's `connected` (set once at slug-connect, App.tsx ~1825). Preload fires once per resume, which is exactly the AC (rehydrate prior-turn art on returning to a saved session).
  - Rationale: minimalist — the AC is preload-on-resume, and `connected` flips true on the resume path before `ready`. Keying on `readyState` would add preload-on-every-socket-reopen, which no test or AC requires.
  - Severity: minor
  - Forward impact: a mid-session WS drop/reopen (without a full resume) does not re-preload; if a future story needs that, key the hook on the `readyState===OPEN` rising edge instead.

### Reviewer (audit)
All logged deviations reviewed and stamped:
- **TEA: AC2 tests assert at the `useImageBus()` boundary, not the feed mechanism** → ✓ ACCEPTED by Reviewer: correct — testing the observable boundary is what made the suite mechanism-agnostic; it held when Dev picked Approach 2 with zero test rewrite.
- **TEA: "No slug → no fetch" guard is non-discriminating in RED** → ✓ ACCEPTED by Reviewer: a valid GREEN guard against an always-on mount; test-analyzer's timing nit is logged as a non-blocking LOW, not a reason to reject the guard.
- **TEA: AC4 `onError` tests pass a prop absent from the current type** → ✓ ACCEPTED by Reviewer: legitimate TDD RED-contract assertion; Dev added the optional `onError` and both compile + pass. No `as any` used.
- **Dev: AC2 chose Approach 2 (second pure `preloadedAssets` input) over Approach 1** → ✓ ACCEPTED by Reviewer: Architect granted sign-off at spec-check; a `useMemo` over `(messages, preloadedAssets)` is genuinely pure, the prop is optional (other callers unaffected), and it bought purge-immunity the RED suite demanded. Sound.
- **Dev: coarse `connected` firing signal (fires once per resume, not per socket reopen)** → ✓ ACCEPTED by Reviewer: matches the AC's resume-rehydration purpose; the mid-session-flap gap is documented with a forward note. NOTE: this same uncleared-state path surfaces the cross-session bleed I logged as a MEDIUM code-review finding — the *firing* decision is accepted; the *reset* gap is the recommended fast-follow.

No undocumented spec deviations found beyond those above.

### Architect (reconcile) — spec-reconcile pass
Definitive deviation manifest verified for SM finish:

- **Entry accuracy:** all five logged deviations (3 TEA + 2 Dev) carry the full 6 fields, and every spec source resolves to a real artifact — `sprint/context/context-story-65-4.md` (validated, authoritative spec), `sprint/context/context-epic-65.md`, and the session's own Delivery Findings. Spec-text quotes and implementation descriptions match the merged code (verified against the diff at spec-check). Reviewer stamped all five ACCEPTED.

- **AC coverage (no deferrals):** all four ACs are DONE in code — AC1 (hook mounted in `AppInner`), AC2 (preloaded URLs reach `useImageBus()` via the Approach-2 second pure input, with URL-dedupe + turn-based ordering + loud-fail on url-less rows), AC3 (App-level wiring test), AC4 (`encodeURIComponent` + `onError`). No AC was descoped or deferred, so the AC-accountability cross-reference is a no-op for this story.

- **Approach-2 contract extension — authoritative disposition:** the governing spec (`context-story-65-4.md` §Technical Guardrails) explicitly framed AC2's feed mechanism as OPEN ("RED/Dev decides") and named Approach 2 as "the cleaner seam if the RED tests show the pollution/purge interactions are fragile." The RED suite pinned purge-survival + cross-source dedupe + turn-based ordering; Dev chose Approach 2; Architect granted sign-off at spec-check (recommendation **A — Update spec**: the ImageBus contract is now "pure over `(messages, preloadedAssets)`", the prop is optional so other callers are unaffected). This is a sanctioned decision within the spec's permitted space, not drift.

- **Verify-phase change accounted for (not a new deviation):** the simplify pass (commit f602191) removed App's redundant `onError` consumer while keeping the hook's unconditional loud log. AC4 requires the *hook* to expose+invoke `onError` (satisfied and tested at the hook level); the spec never required App to *consume* it. So this is within spec — no deviation entry needed.

- **Reviewer findings are fast-follows, not spec deviations:** the MEDIUM cross-session `preloadedAssets`-reset gap and the LOW defense-in-depth items (reducer url-less split-log, `isSessionAsset` guard, URL-scheme allowlist, test tightening) are discovered-limitation/hardening recommendations against behavior the spec did not require. They are captured under `### Reviewer (code review)` for a follow-up; none reverse or contradict a logged deviation.

- **No additional deviations found.**

## TEA Assessment

**Tests Required:** Yes
**Status:** RED confirmed (failing — ready for Dev)

**Test Files:**
- `sidequest-ui/src/hooks/__tests__/useAssetPreload.test.ts` — extended with AC4
  hardening: percent-encoded slug, `onError` on non-ok, `onError` on fetch reject (3 new;
  5 pre-existing AC5 baseline tests retained and still GREEN).
- `sidequest-ui/src/__tests__/asset-preload-app-wiring-65-4.test.tsx` — NEW App-level
  wiring/integration suite (AC1/AC2/AC3 + edges): mount-fires-fetch-once, no-slug guard,
  feed-reaches-gallery-surviving-resume-purge, cross-source URL dedupe, turn-based ordering,
  loud-fail on url-less row. GameBoard stubbed to serialize `useImageBus()` URLs — assertions
  read the observable boundary, so they are mechanism-agnostic (synthetic-messages OR
  second-input both satisfy them).

**Tests Written:** 11 (3 hook + 8 App-wiring) covering AC1–AC4. Mechanism for AC2 left to Dev.
**RED verification (testing-runner, 65-4-tea-red):** 8 new tests FAIL on clean assertions;
6 PASS (5 AC5 baseline + 1 no-slug guard). No harness breakage — all failures trace to the
missing implementation (hook unmounted; no `encodeURIComponent`/`onError`). One unhandled
rejection on the fetch-reject test is the intended RED signal (hook lacks try/catch).

**Wiring gate (CLAUDE.md "Every Test Suite Needs a Wiring Test"):** SATISFIED — the App-level
suite renders `<App/>`, drives a real SESSION_EVENT/IMAGE frame stream over a mocked
WebSocket, and asserts both the production fetch fires AND a preloaded URL renders through
`useImageBus()`. This closes the explicit 65-2 Dev finding "there is no app-integration/wiring
test." Behavior-only; no source-text grep.

### Rule Coverage

| Rule (typescript-review / project) | Test(s) | Status |
|------|---------|--------|
| #10 input validation — URL/path param encoded | `percent-encodes the slug in the fetch URL` | failing (RED) |
| #11 error handling — async reject not swallowed | `invokes onError when the fetch itself rejects` | failing (RED) |
| #4 / No-Silent-Fallbacks — url-less row loud-fails, no blank card | `loud-fails (does not silently gallery-add) a preload row with no URL` | failing (RED) |
| #6 React hooks — no double-fetch / rising-edge only | `does not re-fetch on re-render` + `refetches on a reconnect edge` (pre-existing) | green (baseline) |
| Wiring (CLAUDE.md) — fires from production path, no source-grep | `fetches GET /api/sessions/{slug}/assets exactly once on connect` | failing (RED) |
| Wiring — no always-on mount | `does NOT fetch ... when there is no session slug` | green-vacuous in RED |
| AC2 feed reaches gallery (end-to-end) | `feeds prior-turn CDN URLs into the gallery, surviving the resume purge` | failing (RED) |
| AC2 cross-source dedupe by URL | `dedupes a preloaded asset against a live IMAGE of the same URL` | failing (RED) |
| AC2 turn-based ordering | `orders backfilled assets behind live current-turn images` | failing (RED) |
| #8 test quality — no `as any`, meaningful assertions | self-check (all assert specific values) | satisfied |

**Rules checked:** typescript-review #4, #6, #8, #10, #11 + Wiring (CLAUDE.md) +
No-Silent-Fallbacks (SOUL/CLAUDE) have test coverage. Checks not applicable to a
hook+wiring story (enum exhaustiveness #3, generics #2, module/declaration #5, build-config
#9, perf/bundle #12) are not exercised.
**Self-check:** no `assert(true)` / `let _ =` / always-None assertions; no `as any` casts. The
one non-discriminating-in-RED test (no-slug guard) is logged as a trivial deviation.

### Contract defined for Dev (GREEN)
- `useAssetPreload.ts`: wrap the fetch URL in `encodeURIComponent(slug)`; add an optional
  `onError(err: unknown)` to `UseAssetPreloadArgs`, invoked on `!resp.ok` AND on a thrown/
  rejected fetch (wrap the async IIFE in try/catch); do not call `onAssets` on failure.
- `App.tsx` (`AppInner`): mount `useAssetPreload({ slug, connected, onAssets, onError })`
  with `onAssets` a stable `useCallback`. Decide the firing signal (see Question finding).
- The `onAssets` mapping must loud-fail (`console.error`) on a row with no `url` and not feed
  it to the gallery (No-Silent-Fallbacks).
- Feed mechanism (Approach 1 synthetic IMAGE messages vs Approach 2 second pure
  `preloadedAssets` input) is Dev's choice — but cross-source URL dedupe and turn-based
  ordering require `ImageBusProvider` reducer changes either way (see findings).

**Handoff:** To Dev (Naomi) for GREEN implementation.

## Dev Assessment

**Implementation Complete:** Yes

**Approach:** Approach 2 — a second pure `preloadedAssets` input on `ImageBusProvider`
(not synthetic IMAGE messages). Purge-immune (separate state the reconnect `ready` purge
never touches), no pollution of the four other `messages` consumers, and dedupe+ordering
centralized in one reducer pass. `useMemo` over `(messages, preloadedAssets)` stays pure.

**Files Changed (sidequest-ui):**
- `src/hooks/useAssetPreload.ts` — `encodeURIComponent(slug)`; optional `onError` invoked on
  a non-ok response AND on a thrown/rejected fetch (async IIFE wrapped in try/catch);
  `onAssets` not called on failure.
- `src/providers/ImageBusProvider.tsx` — new optional `preloadedAssets?: SessionAsset[]`
  prop; Pass-3 projection in the reducer — cross-source URL dedupe (live render wins),
  turn-based ordering (backfill behind live via a `created_turn - 1_000_000` timestamp).
- `src/App.tsx` (`AppInner`) — mount `useAssetPreload` at the WebSocket-owning level with
  stable `useCallback` `onAssets`/`onError`; `onAssets` loud-fails (`console.error`) and
  drops url-less ledger rows; new `preloadedAssets` state passed to `ImageBusProvider`.

**Tests:** 14/14 story tests GREEN (8 hook + 6 App-wiring), incl. all 3 AC4 + all AC2 edges.
Regression: ImageGalleryWidget + ScrapbookGallery 48/48 GREEN. **Full UI suite: 1794/1794
pass (187 files).** `tsc --noEmit` exit 0. `eslint` 0 errors (2 pre-existing warnings at
App.tsx:1360/1962, untouched by this change).
**Verified by:** testing-runner (65-4-dev-green, 65-4-dev-green-full) + direct verbose run.

**Branch:** feat/65-4-mount-useassetpreload-imagebus-feed (pushed to origin).

**Self-review (judgment checks):**
- Wired end-to-end: hook mounted in App → fetch → `onAssets` → `preloadedAssets` state →
  `ImageBusProvider` prop → `useImageBus()` gallery. Proven by the App-level wiring test.
- Follows project patterns: mirrors the existing ImageBus reducer Pass structure; hook
  mount mirrors other App-level hooks (`useStateMirror`, `useGenreTheme`).
- All ACs met (AC1 mount, AC2 feed+dedupe+ordering+purge-survival, AC3 wiring test, AC4
  encode+onError).
- Error handling: try/catch + `onError`; loud-fail on url-less rows (No-Silent-Fallbacks).

**Handoff:** To verify (TEA simplify + quality-pass).

> **NOTE (process):** This session file was clobbered mid-green by a `testing-runner`
> subagent overwriting `.session/65-4-session.md` with its own GREEN report (known
> hazard — testing-runner can overwrite the session file). It was reconstructed from
> in-context history (frontmatter, phase tracking, SM + TEA assessments, all Delivery
> Findings and Design Deviations preserved verbatim). `.session/` is gitignored, so no
> git recovery was possible.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with two minor, already-dispositioned decisions)
**Mismatches Found:** 2 (both sanctioned by the context / already logged as deviations — no drift to chase)

AC-by-AC verification against `context-story-65-4.md` and the merged diff (3973d1a..0ca124b):
- **AC1 (mount in AppInner):** Aligned — `useAssetPreload({ slug: slug ?? null, connected, onAssets, onError })` mounted at the WebSocket-owning level (App.tsx ~580) with stable `useCallback` callbacks; fires on the `connected` rising edge.
- **AC2 (feed reaches gallery; pure ImageBus; loud-fail url-less; dedupe; ordering):** Aligned — Approach 2 (`preloadedAssets` prop); `handlePreloadAssets` loud-fails (`console.error`) and drops url-less rows; `ImageBusProvider` Pass-3 does cross-source URL dedupe (live wins) and turn-based ordering (`created_turn - 1_000_000`). The reducer stays a pure `useMemo` over `(messages, preloadedAssets)`.
- **AC3 (App-level wiring test):** Aligned — `asset-preload-app-wiring-65-4.test.tsx` renders `<App/>`, drives the WS frame stream, and asserts both the production fetch fires AND a preloaded URL reaches `useImageBus()`. Closes the 65-2 "no app-integration/wiring test" finding.
- **AC4 (encode + onError):** Aligned — `encodeURIComponent(slug)`; `onError` invoked on non-ok AND on a thrown/rejected fetch (try/catch); `onAssets` not called on failure.

- **Approach 2 (second pure `preloadedAssets` input) chosen over the context's Architect-leaned Approach 1** (Extra-in-code — Architectural, Minor)
  - Spec: context framed AC2 as OPEN ("RED/Dev decides"); Architect *leaned* reuse-first to synthetic IMAGE messages, with Approach 2 named as "the cleaner seam if the RED tests show the pollution/purge interactions are fragile."
  - Code: added a `preloadedAssets?: SessionAsset[]` prop to `ImageBusProvider`; a `useMemo` over `(messages, preloadedAssets)`.
  - Recommendation: **A — Update spec.** **Architect sign-off GRANTED.** The RED suite pinned purge-survival, cross-source dedupe, AND turn-based ordering — exactly the fragility that tips the decision to Approach 2. A second pure input does NOT violate the 65-2 "pure reducer" freeze: purity means output-determined-by-inputs, not single-input. The contract is legitimately extended from "pure over `messages`" to "pure over `(messages, preloadedAssets)`". The prop is optional, so every other `ImageBusProvider` caller is unaffected. Already logged under Dev deviations.

- **Hook firing signal is App's coarse `connected` (fires once per resume, not per socket reopen)** (Ambiguous-spec — Behavioral, Minor)
  - Spec: AC1 says the hook fires "on the reconnect edge with the current session slug"; the firing signal was a TEA-flagged open question (coarse `connected` vs `readyState===OPEN`).
  - Code: passes App's `connected` (set once at slug-connect, App.tsx ~1825). Preload fires once on the resume path; a mid-session WS drop/reopen without a full resume does not re-preload.
  - Recommendation: **C — Clarify spec.** The AC's purpose is resume rehydration, and `connected` flips true on exactly that path. The unhandled case (mid-session socket flap) is out of this story's scope and is documented as a Dev deviation with a forward note (key on `readyState===OPEN` if a future story needs it). No code change.

**Decision:** Proceed to verify. No hand-back to Dev — both items are already-decided, sanctioned deviations (one A, one C), not unaddressed drift. Implementation is end-to-end wired, all four ACs aligned, full UI suite + typecheck + lint green.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (3 impl + 2 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | 1 medium (extract a generic `filterByField`/`filterValidAssets` helper from `handlePreloadAssets`) — flagged, not applied |
| simplify-quality | 3 findings | 2 high (double-log on preload failure) applied as 1 fix; 1 medium (name the `1_000_000` sentinel) flagged |
| simplify-efficiency | 1 actionable + 3 low | 1 medium (default-param `preloadedAssets = []` identity churn) flagged; 3 low (Pass-3 explicit-undefined fields, App callbacks, rising-edge effect) confirmed intentional — no action |

**Applied:** 1 fix (commit f602191)
- **Double-log dedup** (quality, high ×2): the hook `console.error`s on a preload failure AND App's `onError` consumer logged again. **Applied the safe direction:** kept the hook's unconditional `console.error` (preserves No-Silent-Fallbacks even when `onError` is absent) and removed App's redundant `handlePreloadError` + `onError` arg. NOTE: the teammate's suggested direction (strip the hook's logs, let the mount site own logging) was **rejected** — `onError` is optional, so that would make failures silent for any caller that omits it. The hook's `onError` contract is unchanged and still covered by the hook unit tests.

**Flagged for Review (medium — not applied):**
- **Name the `1_000_000` sentinel** (quality) — extract `const PRELOAD_TIMESTAMP_OFFSET` in `ImageBusProvider.tsx`. Pure readability; deferred to keep the verify diff minimal. Reviewer may apply.
- **Default-param `preloadedAssets = []` identity churn** (efficiency) — latent footgun only; the sole caller (App) always passes the state array, so the default never triggers a useMemo refire today. Hoist a module-level `EMPTY` const if a second caller appears.
- **Extract a generic validation helper** (reuse) — `handlePreloadAssets`'s filter-validate-accumulate loop matches the `readStringArray`/`readNpcArray` shape; single use today, so extraction is speculative future-proofing.

**Noted (low):** Pass-3 explicit-`undefined` fields (type-safety legibility, intentional), App callbacks (stable + load-bearing), the rising-edge `wasConnected`/`cancelled` guards (correctness-bearing). No action.

**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Quality Checks:** All passing — `tsc --noEmit` clean; `eslint` 0 errors (2 pre-existing
warnings at App.tsx:1360/1962, untouched); affected suites 62/62; **full UI suite
1794/1794 (187 files)** re-run after the simplify commit.

**Process note:** test runs in this verify pass were executed directly (vitest/tsc/eslint)
rather than via the `testing-runner` subagent — that subagent twice overwrote
`.session/65-4-session.md` with its own report during this story (known clobber hazard),
so direct runs were used to protect the session file. Results are unchanged in substance.

### Delivery Findings (verify)
- No new upstream findings during test verification. The double-log smell was a same-story
  Dev artifact, fixed in-phase (commit f602191); the three medium findings are non-blocking
  polish flagged for the Reviewer.

**Handoff:** To Reviewer (Chrisjen Avasarala) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (62/62 tests GREEN, tsc clean, 0 lint errors) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 7 | confirmed 7 (1 MED + 6 LOW after adjudication); 2 subagent-HIGHs downgraded with evidence |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 3 (all LOW, rule-matching — downgraded not dismissed) |
| 4 | reviewer-test-analyzer | Yes | findings | 8 | confirmed 8 (4 MED test-tightening + 4 LOW, all non-blocking) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — assessed manually (see [DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — assessed manually (see [TYPE]) |
| 7 | reviewer-security | Yes | findings | 3 | confirmed 3 (1 MED rule#10 + 2 LOW; downgraded for LAN/trusted arch) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — verify-phase simplify already applied 1 fix (see [SIMPLE]) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — assessed manually (see [RULE]) |

**All received:** Yes (5 enabled returned, 4 disabled via workflow.reviewer_subagents)
**Total findings:** confirmed 21 (1 MED behavioral + 7 MED test/security-tightening + 13 LOW), 0 dismissed, 0 deferred. **0 Critical, 0 High → no blockers.**

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced (user input → render):** a saved session's `slug` (router) → `useAssetPreload` fires on the `connected` rising edge → `GET /api/sessions/${encodeURIComponent(slug)}/assets` → `(await resp.json()) as SessionAsset[]` → `handlePreloadAssets` (App) drops+loud-fails url-less rows → `setPreloadedAssets(valid)` → `ImageBusProvider` Pass-3 (URL-dedupe vs live, `created_turn - 1_000_000` ordering) → `useImageBus()` `GalleryImage[]` → `<img src={entry.url}>` (ScrapbookGallery:215/312). Every hop is covered by the App-level wiring test; the fetch is encoded; failures are logged loudly.

### Observations (≥5; subagent findings tagged + manual coverage for disabled lanes)

- **[EDGE][MEDIUM] Cross-session stale preload bleed.** `preloadedAssets` is never cleared on `handleLeave`/disconnect (App.tsx — `handleLeave` resets `messages`/`connected` but not `preloadedAssets`). Switching to a *different* session in one page-lifetime can briefly render the prior session's art before the new preload resolves (ImageBusProvider mounts on `ready` with the stale array). **Adjudication:** the dominant use case (single-player resume to the *same* save) is unaffected — same-session preloads SHOULD survive, that's the feature. Transient, self-correcting (next `onAssets` overwrites), no data corruption, no security. Medium → non-blocking. **Recommend** `setPreloadedAssets([])` in `handleLeave` (and/or reset on slug-change rising edge) as a fast-follow.
- **[EDGE] `created_turn ≥ 1_000_000` ordering — DOWNGRADED HIGH→LOW (challenge).** The subagent claimed `created_turn ≥ messages.length` sorts after live. **That is incorrect:** backfill `timestamp = created_turn - 1_000_000` stays **negative** for any `created_turn < 1e6` regardless of `messages.length`, and all live timestamps are ≥ 0, so backfill always sorts behind live. The only real break needs **1,000,000 turns** in one session (not messages) — physically unreachable, and already logged as a Dev deviation. Evidence: `ImageBusProvider.tsx` Pass-3 timestamp formula + the existing `sort((a,b)=>a.timestamp-b.timestamp).reverse()`. LOW. A secondary sort key (`source: preload < live`) would be a cleaner future-proof — recommend, non-blocking.
- **[SILENT][LOW] Reducer url-less skip is silent.** `if (!url || seenUrls.has(url)) continue;` (ImageBusProvider Pass-3) collapses a contract-violating url-less row and an expected dedup into one un-logged `continue`. The App boundary already loud-fails+drops url-less rows (the only production source), so this branch is unreachable defense-in-depth — but per the hard No-Silent-Fallbacks rule I **confirm, not dismiss**, at LOW. **Recommend** splitting the guard and `console.error`-ing the `!url` case as a reducer-level second line. Same applies to the duplicate-URL dedup (an anomalous ledger dup is silently dropped) — a `console.error` there is reasonable defense-in-depth.
- **[SILENT][LOW] `onError` optional / no App consumer.** The hook `console.error`s preload failures unconditionally (loud even without `onError` — verified, `useAssetPreload.ts` non-ok + catch both log), but App passes no `onError`, so failures are console-only with no UI surface. **Adjudication:** preload is a best-effort graceful-degradation path (ADR-006) — a failure leaves the gallery to populate from live renders; the live session is unaffected. `console.error` is this codebase's established loud-fail level (matches the 65-2 reviewer's acceptance of the same hook). Making `onError` *required* (subagent suggestion) would break the 5 baseline 65-2 hook tests and exceed scope. Confirmed at LOW, non-blocking.
- **[SEC][MEDIUM→LOW] Rule #10 — `as SessionAsset[]` without runtime validation.** `(await resp.json()) as SessionAsset[]` (useAssetPreload.ts) accepts server fields verbatim; `url` flows to `<img src>`. **Adjudication:** rule-matching → confirmed not dismissed; downgraded LOW because (a) the cast is **pre-existing from 65-2** (not introduced here), (b) the source is the server's own asset ledger — same trust as live IMAGE messages that already flow unvalidated to the same gallery, (c) documented LAN/trusted-server, unauth-by-design REST surface. **Recommend** a lightweight `isSessionAsset` type-guard in `handlePreloadAssets` as defense-in-depth.
- **[SEC][LOW] `<img src>` scheme not allowlisted (XSS defense-in-depth).** `url` → `<img src={entry.url}>` with no `^https?://` check. **Verified safe:** `<img src="javascript:…">` does not execute in modern Chrome/Safari/Firefox (only `href` gets React's scheme block, but img-src is not a script sink in current browsers), and the URL shares the existing live-image trust path. No new trust boundary. Recommend a scheme allowlist at the App filter as cheap hardening. LOW.
- **[SEC][LOW] Unencoded slug in the failure log.** `useAssetPreload.ts` error log interpolates raw `${slug}` while the fetch used `encodeURIComponent(slug)` — the logged URL won't match the real request for slugs needing encoding. Cosmetic; console-only. Recommend encoding the log string to match. LOW.
- **[TEST][MEDIUM] Vacuous `console.error` assertion.** The url-less wiring test asserts `expect(errorSpy).toHaveBeenCalled()` — any incidental console.error satisfies it, not specifically the url-less guard (rule #8). **Recommend** `toHaveBeenCalledWith('useAssetPreload: ledger row has no resolved url — dropping', expect.objectContaining({ r2_key: … }))`. Non-blocking (RED proved the guard fires; this tightens GREEN).
- **[TEST][MEDIUM] Coverage gaps.** (a) no assertion of backfill-vs-backfill relative order (turn-2 before turn-1); (b) no direct `ImageBusProvider` unit tests for the Pass-3 prop (dedup / url-less skip / empty array) — only exercised through the full App stack; (c) `onError` tests don't assert the error payload (`message: 'asset preload failed: 503'`). All MEDIUM test-tightening, non-blocking. **Recommend** as a test fast-follow.
- **[TEST][LOW] async `vi.mock` factory seam — challenged.** The subagent worried the async GameBoard-stub factory could resolve to an empty context and pass-while-broken. **Counter-evidence:** the core feed tests assert `urls.toContain(PRELOAD_ROWS[x].url)` — an empty `[]` context makes `toContain` **fail**, so a broken-to-empty wiring fails the test (the desired behavior). The suggested `length > 0` guard is redundant with `toContain`. LOW.
- **[DOC] (comment lane manual)** — comments in the diff are accurate, not stale: the hook docstring (`Fires once per (re)connect edge`), the App "no onError consumer" rationale, the ImageBusProvider purity/purge comment, and the Pass-3 dedup/timestamp comment all match the code. The Pass-3 "skip silently if one slips through" comment honestly documents the [SILENT] behavior above. No misleading docs. LOW.
- **[TYPE] (type lane manual)** — `preloadedAssets?: SessionAsset[]` and `onError?: (error: unknown) => void` are honest optionals; `unknown` is the correct catch type (rule #11); `import type { SessionAsset }` is type-only; the GalleryImage projection is fully typed. The one smell is the pre-existing `as SessionAsset[]` (covered under [SEC]/#10). No new `as any`. LOW.
- **[SIMPLE] (simplifier lane manual)** — verify-phase already deduped the double-log (commit f602191). Pass-3's explicit-`undefined` fields are intentional type-safety. No over-engineering. Clean.
- **[VERIFIED] No-Silent-Fallbacks at the App boundary** — `handlePreloadAssets` (App.tsx) loud-fails (`console.error`) AND drops url-less rows; complies with the `<critical>` rule. Evidence: the filter loop logs then `continue`s, and only `valid` rows reach `setPreloadedAssets`.
- **[VERIFIED] Wiring** — App mounts the hook; the App-level integration test drives a real WS frame stream and asserts the encoded fetch fires AND a preloaded URL renders via `useImageBus()`. Closes the 65-2 "no app-integration/wiring test" finding. Evidence: `asset-preload-app-wiring-65-4.test.tsx` + full UI suite 1794/1794.

### Rule Compliance (typescript-review checklist + project rules)

| Rule | Instances checked | Verdict |
|---|---|---|
| #1 type-safety escapes (no `as any`/ts-ignore) | all 3 impl files | Compliant (only `as SessionAsset[]`, pre-existing — see #10) |
| #4 `??` vs `||` on nullable | Pass-3 `entity_ref || undefined`, `asset_type || undefined` | Compliant-with-rationale — `""` genuinely means "absent" for alt/tier; values are never the 0/"" the rule guards; LOW note |
| #6 React hooks deps | `useAssetPreload` effect `[slug,connected,onAssets,onError]`; `handlePreloadAssets` `useCallback([])` | Compliant (stable callbacks, correct deps) |
| #10 input validation (URL encode; runtime-validate API JSON) | `encodeURIComponent(slug)` ✓; `as SessionAsset[]` ✗ | encode Compliant; cast = LOW finding (pre-existing, LAN-trust) — confirmed not dismissed |
| #11 error handling (catch unknown, no swallow) | hook try/catch | Compliant (err forwarded+logged, not swallowed) |
| #8 test quality (specific assertions) | url-less test `toHaveBeenCalled()` | LOW finding (tighten to `toHaveBeenCalledWith`) — confirmed |
| No-Silent-Fallbacks `<critical>` | App url-less drop (loud ✓); reducer url-less skip (silent — LOW); onError optional (console-only — LOW) | App boundary Compliant; reducer/onError confirmed LOW (downgraded, not dismissed) |
| OTEL principle | — | N/A — pure UI story, no backend subsystem decision |

### Devil's Advocate

Suppose this is broken. A malicious or compromised asset ledger returns rows with a `url` of `javascript:fetch('//evil')` or a `data:text/html` URI. The client casts the body `as SessionAsset[]` with zero runtime validation and pipes `url` straight into `<img src>`. Is that an exploit? In a 1998 browser, yes — `<img src="javascript:…">` once executed. In current Chrome/Safari/Firefox it does not; img-src is not a script-execution sink, SVG loaded via `<img>` is script-sandboxed, and `data:` images can't run script. The ledger is also the server's *own* DB, populated by the daemon's R2 upload — the same provenance as live IMAGE URLs that already flow unvalidated into the identical `<img src>`. So this story opens no new trust boundary; the realistic worst case is a broken-image icon. Still, the `as`-cast with no `isSessionAsset` guard is the weakest link and worth a defense-in-depth predicate.

What would a confused user trigger? Session-switching without a page reload: leave session A, join session B. `preloadedAssets` isn't cleared on leave, so B's gallery can flash A's art for a few hundred ms until B's preload lands. Confusing, not corrupting — and the dominant single-player "reopen my save" path never hits it. What would a stressed runtime produce? A truncated/HTML ledger response → `resp.json()` throws → caught → `onError` (and the gallery simply stays empty; the live session is untouched). A 10,000-row ledger → a synchronous JSON parse hitch on mount; realistically a save has dozens of assets, not thousands, so no practical freeze. A `created_turn` of 0 or negative → sorts to the oldest slot (negative timestamp); benign unless a downstream widget indexes on `turn_number`, which none in this diff do. Two ledger rows with the same `url` → the second is silently deduped (no log) — an anomaly that should arguably be loud, but harmless. Race: the hook fetch resolves after unmount → the `cancelled` guard suppresses `onAssets`/`onError` (the `console.error` still fires, which is fine). Nothing here corrupts state, leaks across the trust boundary, or loses the player's live session. No Critical/High surfaces — the worst honest outcome is a transient cross-session image flash and an unvalidated-but-same-trust image URL.

### Deviation Audit

(See `### Reviewer (audit)` under Design Deviations.)

**Handoff:** To SM (Camina Drummer) for finish-story. APPROVED — no blocking findings; recommended non-blocking fast-follows captured below.

### Reviewer (code review)
- **Improvement** (non-blocking, MEDIUM): Clear `preloadedAssets` on session exit/switch — `setPreloadedAssets([])` in `handleLeave` (and/or on the slug-change rising edge) to prevent a transient prior-session image flash when switching saves without a page reload. Affects `sidequest-ui/src/App.tsx`. *Found by Reviewer (edge-hunter) during code review.*
- **Improvement** (non-blocking, LOW): Split the Pass-3 guard so a url-less preloaded row `console.error`s at the reducer (defense-in-depth) instead of a bare silent `continue`; optionally log the duplicate-URL dedup. Affects `sidequest-ui/src/providers/ImageBusProvider.tsx`. *Found by Reviewer (silent-failure-hunter) during code review.*
- **Improvement** (non-blocking, LOW): Add an `isSessionAsset` runtime type-guard in `handlePreloadAssets` (rule #10 defense-in-depth) and a `^https?://` URL-scheme allowlist before feeding the gallery; encode the slug in the hook's failure log to match the fetched URL. Affects `sidequest-ui/src/hooks/useAssetPreload.ts` + `src/App.tsx`. *Found by Reviewer (security) during code review.*
- **Improvement** (non-blocking, MEDIUM): Tighten tests — assert the url-less `console.error` payload (`toHaveBeenCalledWith`), add a backfill-vs-backfill ordering assertion, assert the `onError` error payload, and add direct `ImageBusProvider` unit tests for the Pass-3 `preloadedAssets` logic (dedup / url-less skip / empty array). Affects `sidequest-ui/src/__tests__/asset-preload-app-wiring-65-4.test.tsx`, `src/hooks/__tests__/useAssetPreload.test.ts`, and a new `ImageBusProvider` unit test. *Found by Reviewer (test-analyzer) during code review.*