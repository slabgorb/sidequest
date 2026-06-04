---
parent: context-epic-65.md
workflow: tdd
---

# Story 65-4: Mount useAssetPreload in App + ImageBus preload feed (AC5 follow-up from 65-2)

## Business Context

Story 65-2 closed the **runtime asset loop** on the server: every image the daemon
uploads to R2 during play is now recorded against the save in a Postgres `asset_ledger`,
and `GET /api/sessions/{slug}/assets` returns those rows with resolved CDN URLs. 65-2 also
shipped the **`useAssetPreload` hook** (fetch-on-reconnect-edge) — but a Doctor decision
(2026-05-27) deliberately split the *app wiring* out because feeding the fetched URLs into
the **pure-reducer** `ImageBusProvider` is a genuine design decision, not a mechanical
mount. 65-2 therefore delivered a hook with **no production consumer** — a half-wired
feature by the project's own definition.

This story finishes the resume experience the whole loop exists for: when a player returns
to a saved session, prior-turn portraits and scene illustrations **rehydrate from R2 with
no re-render**. That serves the playgroup directly — Alex and the household don't sit
through a blank gallery re-generating art they already saw, and Keith's two-clone content
workflow gets the durable-art payoff 65-1/65-2 built toward. Until this story lands, the
ledger and endpoint are real but invisible to the player.

## Technical Guardrails

> Architect (Naomi) observations from context creation are folded into the guardrails
> below. The central AC2 mechanism decision is **deliberately left open** for the RED/design
> phase — this section frames the trade-offs and pins the hard constraints, it does not
> pick the approach.

**Mount point (settled).** `useAssetPreload` mounts inside `AppInner`
(`sidequest-ui/src/App.tsx`) — the WebSocket-owning level the hook's own docstring
mandates, and the level that already owns `messages`/`setMessages`, `connected`, and
`useGameSocket`. `slug` comes from `useParams` (the hook already accepts `string | null`);
`connected` is local state. **`onAssets` must be a `useCallback`** so the hook's effect
deps `[slug, connected, onAssets]` don't refire every render — an unstable `onAssets` turns
the rising-edge guard into a churn source.

**ImageBus stays a pure reducer (FIRM, inherited from 65-2 Architect).**
`ImageBusProvider` (`sidequest-ui/src/providers/ImageBusProvider.tsx`) is a `useMemo`
reducer over `messages: GameMessage[]` with **no fetch/lifecycle/side effects**. It
projects `MessageType.IMAGE` (requires a truthy `url`; dedupes by `render_id`; reads
`turn_number`, `tier`, `alt`, `caption`, `handout`) and `MessageType.SCRAPBOOK_ENTRY`
(keyed by `turn_id`); output `GalleryImage[]` is sorted by a `timestamp` that is currently
just the **message array index**, then reversed (newest first). Do **not** add fetch or
lifecycle logic to this component.

**The AC2 design question — how do `SessionAsset[]` rows reach the pure reducer?** Two
candidate approaches, both viable; RED/Dev decides:

- **Approach 1 — synthetic IMAGE messages.** `onAssets` maps rows →
  `MessageType.IMAGE` GameMessages (`url ← row.url`, `render_id ← r2_key`,
  `turn_number ← created_turn`) and `setMessages(prev => [...prev, ...synthetic])`. *Pro:*
  zero ImageBus change, reuses the existing IMAGE projection — the reuse-honest path.
  *Costs to engineer out (not hope away):* (a) **render_id namespace collision** with live
  renders — prefix synthetic ids (e.g. `preload:${r2_key}`) so the id-spaces provably can't
  collide; (b) the **reconnect purge** can wipe injected messages (see hazard below);
  (c) **cross-consumer pollution** — `messages` is also read by `useStateMirror`,
  `useGenreTheme`, `useAudioCue`, and the MP-03 `seenEventKeysRef` append; synthetic IMAGE
  rows must not perturb those; (d) **ordering** — index-based timestamps make backfilled
  old-turn images sort *newer* than live ones, which likely forces a `turn_number`-based
  sort key (a reducer change that erodes the "zero ImageBus change" pro).
- **Approach 2 — second pure input.** Add a `preloadedAssets` prop to `ImageBusProvider`
  merged in a Pass-0 of the reducer. A `useMemo` over `[messages, preloadedAssets]` is
  **still a pure reducer** (purity = output-determined-by-inputs, not single-input) — frame
  this to the 65-2 Architect as a *second pure source*, not a side effect, and get sign-off
  on the contract-signature change. *Pros:* no fake messages → zero pollution of the four
  message consumers; the reconnect purge (which only filters `messages`) **cannot wipe**
  `preloaded`, so backfill survives reconnect for free. *Cons:* changes the frozen contract;
  duplicates a slice of the IMAGE projection unless refactored into a shared helper.

  *Deciding axis:* cross-consumer-pollution + reconnect-purge survival (favors 2) vs.
  contract-freeze preservation (favors 1). Architect's reuse-first lean is Approach 1 with
  its costs paid explicitly; Approach 2 is the cleaner seam if the RED tests show the
  pollution/purge interactions are fragile.

**No-Silent-Fallbacks gate (both approaches).** A preload row arriving with
`url === undefined` is a **server-contract violation** (the endpoint promised resolved CDN
URLs) — the mapping layer must `console.error` on a url-less row, **not** silently skip it.
(The reducer's existing silent `continue` on missing url is correct for *live* placeholder
IMAGE messages whose URL arrives later; it is wrong for a *preload* row.) Mirror the loud
drop already used by `parseScrapbookEntry`.

**Carry-over fixes from 65-2 review (in scope here, non-negotiable):**
- `encodeURIComponent(slug)` on the fetch path in `useAssetPreload.ts` (currently absent,
  line ~47).
- An **`onError` callback** on `UseAssetPreloadArgs`. The hook currently `console.error`s
  and returns on `!resp.ok` (loud, but App has no hook to surface it) — a silent return
  while App believes preload may still fire is itself a soft silent-fallback. `onError`
  lets the mount site surface the failure through the same channel the WS error uses.

**Key files:**
- `sidequest-ui/src/App.tsx` (`AppInner`) — mount the hook; `onAssets`/seam wiring.
- `sidequest-ui/src/hooks/useAssetPreload.ts` — add `encodeURIComponent` + `onError`.
- `sidequest-ui/src/providers/ImageBusProvider.tsx` — touched only if Approach 2 (or a
  `turn_number` sort key under Approach 1).
- `sidequest-ui/src/hooks/__tests__/useAssetPreload.test.ts` — existing unit tests
  (extend for `onError` + encoded slug).

## Scope Boundaries

**In scope:**
- Mount `useAssetPreload` in `AppInner` on the WebSocket-owning level (AC1).
- Implement the chosen feed mechanism so fetched CDN URLs reach the ImageBus gallery (AC2).
- A mandatory **App-level wiring/integration test** proving the hook is mounted and the
  `onAssets → seam → ImageBus` path is reachable from a production code path (AC3).
- `encodeURIComponent(slug)` + `onError` on the hook, with test coverage (AC4).
- Whatever reducer change the chosen approach requires (synthetic-id namespace + sort key,
  or the `preloadedAssets` second input) — including its tests.

**Out of scope:**
- **Server / backend** — the ledger, the REST endpoint, and CDN-URL resolution all shipped
  in 65-2. No server change.
- **Daemon / content** — untouched.
- Backfilling ledger rows for assets generated before 65-2 shipped.
- The deferred **AC6 runtime-artifact R2 audit** (separate follow-up from 65-2).
- Any change to how *live* in-session renders flow through IMAGE messages — this story only
  adds the *preload/backfill* path.

## AC Context

**AC1 — `useAssetPreload` is mounted in `AppInner`.**
- The hook is called inside `AppInner` with the router `slug`, the local `connected` state,
  and a stable `useCallback` `onAssets`.
- It fires its fetch exactly once on the rising edge of `connected` (initial connect AND
  reconnect), and **not** on unrelated re-renders.
- Edge: with no `slug` (lobby / pre-session), the hook issues no fetch.
- Test: an App-level render driving `connected` false→true asserts a single
  `GET /api/sessions/{encoded-slug}/assets`; no-slug asserts no fetch.

**AC2 — fetched CDN URLs reach the ImageBus gallery (the feed mechanism).**
- `onAssets(rows)` results in the preloaded portraits/illustrations appearing as
  `GalleryImage`s via `useImageBus()` — without emitting any render request for
  already-ledgered assets.
- The mechanism keeps `ImageBusProvider` pure (synthetic messages OR a second pure input).
- A url-less row fails loudly (console.error), is not silently dropped into the gallery.
- Edge: if a preloaded asset *also* arrives as a live IMAGE this session, the gallery shows
  **one** card, not two (cross-source dedupe — `url` is the only field guaranteed common to
  a preload row and a live IMAGE; `r2_key` and `render_id` are different namespaces).
- Edge: a backfilled `created_turn=2` asset must not sort *ahead of* a live `turn_number=40`
  image (ordering must be turn-based, not array-index-based, once backfill exists).
- Test: feed sample rows; assert resolved URLs render in the gallery; assert dedupe and
  ordering on the two edges above.

**AC3 — App-level wiring test (MANDATORY — closes the 65-2 "no app-integration/wiring test"
finding).**
- Render `AppInner`/App with a mocked `fetch`, a routed `slug`, and `connected` false→true.
- Assert `fetch` was called with `/api/sessions/${encodeURIComponent(slug)}/assets` exactly
  once on the rising edge — proves the hook is *actually mounted in the tree*, not merely
  importable.
- **Load-bearing assertion:** query `useImageBus()`/`ScrapbookGallery` and assert a
  preloaded URL renders as a `GalleryImage` — proves the `onAssets → seam → ImageBus` path
  is wired end-to-end (the AC2 contract), which a hook-only unit test cannot.
- Negative wiring assertion: with no `slug`, `fetch` is not called (guards against an
  always-on mount).
- No source-text grep — behavior only.

**AC4 — hook hardening (`encodeURIComponent` + `onError`).**
- The fetch URL encodes the slug: `/api/sessions/${encodeURIComponent(slug)}/assets`.
- `UseAssetPreloadArgs` gains an `onError` callback invoked on `!resp.ok` (and on a thrown
  fetch), so the mount site can surface the failure; the hook still logs loudly.
- Test: a slug with a `/` or space is encoded in the fetched URL; a non-ok response invokes
  `onError` (and does not call `onAssets`).

## Assumptions

- **The CDN `url` on each ledger row is authoritative and resolved server-side** (65-2
  `resolve_asset_url`). The client does not construct URLs from `r2_key`; a missing `url`
  is a contract violation, not a fallback-to-construct case.
- **`slug` and `connected` are both reachable in `AppInner`** at the mount site (they are —
  `slug` via `useParams`, `connected` via local state). If the chosen approach needs a
  post-`ready` phase signal (see hazard below), `sessionPhaseRef`/the `ready` transition is
  available in the same component.
- **Reconnect-ordering hazard (Approach 1 specifically):** the hook fires on the rising
  edge of `connected` (socket open), which can fire **before** the `ready` SESSION_EVENT
  that purges `messages` to SESSION_EVENT-only for the server's last_seen_seq replay. If
  synthetic IMAGE messages are appended *before* that purge, the purge filter **deletes
  them** and the preload is silently lost (a No-Silent-Fallbacks violation by omission).
  Approach 1 must therefore inject **after** the purge+replay (gate on the post-`ready`
  phase or re-inject after it), and a RED test must reproduce connected→inject→`ready`-purge
  and assert preloaded images survive. **Approach 2 is immune** — `preloadedAssets` is
  separate state the purge never touches. If this assumption (that injection can be ordered
  after the purge) proves false, that is a strong signal to take Approach 2; log it as a
  Design Deviation and notify SM.
- **Open questions for Dev/RED** (do not block setup; resolve during design):
  1. Does the live render for a preloaded asset re-arrive as an IMAGE message in the same
     session? If yes, both approaches need cross-source dedupe (likely by `url`).
  2. Confirm the authoritative gallery sort key becomes `turn_number`/`created_turn` (index
     as tiebreaker) — a reducer change regardless of approach, its own RED test.
  3. (Approach 1 only) which phase signal gates injection — does the hook need a new
     "fire after ready" arg, or can `onAssets` read the phase from `AppInner`?
