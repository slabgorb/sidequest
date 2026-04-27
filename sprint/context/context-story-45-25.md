---
parent: sprint/epic-45.yaml
workflow: tdd
---

# Story 45-25: Replace MP-01 slug-connect 300ms setTimeout with effect-based readyState=OPEN wait

## Business Context

MP-01 introduced the slug-based connect handshake — `connect()` opens the
WebSocket, then a hard-coded `setTimeout(..., 300)` schedules the
`SESSION_EVENT{event: "connect", game_slug, last_seen_seq, player_name}`
payload. The 300ms is an *empirical guess* that the socket will have
transitioned to `OPEN` by then. Today, on a healthy local dev box, it does.
Under load (slow Wi-Fi, hibernate-resume, the kind of network the playgroup
actually plays on), arbitrary timers in WS handshake paths are a known
regression vector — the timer expires while the socket is still `CONNECTING`,
the `send()` no-ops or queues against an undefined-state socket, and the
session never registers with the server.

This is **not a player-facing bug today**, but it is exactly the class of
latent flake that turns into a "my game won't connect" report from Alex on a
Sunday session. ADR-038 (WebSocket Transport Architecture) treats the
WS lifecycle as the canonical event surface; ADR-027 (Reactive State
Messaging) treats UI state as a function of incoming WS messages. A
hard-coded 300ms timer is at odds with both: it neither subscribes to the
lifecycle event nor reacts to the state. The fix is small, contained, and
removes a foot-gun before it fires.

Audience framing: the playgroup never sees the win. Engineering hygiene
that prevents flaky reconnects from harming Alex's pacing is the value;
Sebastien's GM-panel lie-detector is downstream of a connection that
actually completed, so the predictability matters there too.

## Technical Guardrails

### The smell, exactly

`sidequest-ui/src/App.tsx:1238–1260` (verified). The slug-connect effect
calls `connect()` synchronously, then schedules the SESSION_EVENT 300ms
later via `setTimeout`. The comment at lines 1240–1242 admits the design
("300ms gives the socket one event-loop tick to transition to OPEN before
the SESSION_EVENT connect is sent"). The send goes via
`sendRef.current?.(...)` — a ref-backed mirror of `useGameSocket().send`
maintained at `App.tsx:834,860`.

### Existing mechanism to wire through

The hook `useGameSocket` at `sidequest-ui/src/hooks/useGameSocket.ts:11–17`
already exposes `readyState: number` (re-exported from `useWebSocket`,
`sidequest-ui/src/hooks/useWebSocket.ts:81`). `readyState` is a reactive
React state — it transitions through `CONNECTING → OPEN` as the socket
opens, and React re-renders when it changes. This is the seam to use.

There is already precedent in `App.tsx`: two effects at `App.tsx:1293–1300`
and `App.tsx:1307–1332` already gate work on
`readyState === WebSocket.OPEN && prevReadyState.current !== WebSocket.OPEN`.
The slug-connect handshake should follow the same shape — a `useEffect`
that fires on the OPEN transition and dispatches the pending SESSION_EVENT
payload. **Reuse, don't reinvent**: the `prevReadyState` ref pattern
already lives at `App.tsx:1285`.

### Replacement shape

The current synchronous-then-delayed flow:

1. Latch `slugConnectFired.current = true`
2. `connect()` (synchronous; opens the socket but returns before OPEN)
3. `setConnected(true)`
4. `setTimeout(() => sendRef.current?.({SESSION_EVENT...}), 300)`

becomes a two-phase flow keyed off `readyState`:

1. Inside the slug-fetch `.then()`: stash the pending SESSION_EVENT
   payload in a ref (e.g., `pendingConnectPayloadRef`), latch
   `slugConnectFired`, call `connect()`, `setConnected(true)`. **Do not
   send.**
2. A new `useEffect([readyState, ...])`: when `readyState ===
   WebSocket.OPEN` AND `pendingConnectPayloadRef.current` is non-null,
   call `sendRef.current?.(payload)` and clear the ref. Synchronous-OPEN
   case is naturally covered: if `connect()` resolved synchronously
   (already-open socket, e.g. StrictMode remount), the effect runs on
   mount with `readyState === OPEN` and fires.

The effect is the single dispatch site; the timer is gone.

### Test surface (TDD — tests before implementation)

Per CLAUDE.md "Every Test Suite Needs a Wiring Test" — and per epic
guidance, this is `workflow: tdd` because the change is small and
self-contained, but the wiring test is still mandatory.

Use `jest-websocket-mock` (`WS` from `jest-websocket-mock`) — already the
project's WS test convention; see `sidequest-ui/src/__tests__/lobby-start-ws-open.test.tsx:39`
for the import line and `:144` for the `new WS(wsUrl, { jsonProtocol: true })`
pattern. Existing tests like `lobby-start-ws-open.test.tsx` and
`mp-03-event-sync-wiring.test.tsx` already drive the slug-connect path
end-to-end through React; the new tests should plug into the same fixture
shape. Reference: `.pennyfarthing/skills/pf-testing/testing.md`.

Three required tests:

1. **OPEN-after-connect (the common case).** Mount AppInner against a
   `jest-websocket-mock` server, navigate to `/solo/<slug>`, await
   `server.connected`, then `await server.nextMessage`. Assert the
   message is `SESSION_EVENT{event: "connect", game_slug, player_name,
   last_seen_seq: 0}`. **Crucially**: no `vi.advanceTimersByTime(300)`
   call should be needed for this to pass. Today's test
   (`lobby-start-ws-open.test.tsx:159–167`) likely passes only because
   `jest-websocket-mock` resolves OPEN within the macrotask the timer
   fires on; the new effect should make this synchronous-on-OPEN.

2. **OPEN-already (StrictMode-remount / cached socket).** With a
   pre-opened mock server such that `readyState` is `OPEN` at the moment
   the effect mounts, assert SESSION_EVENT fires from the mount-time
   effect run. (Validates the synchronous-readyState path of the
   effect.)

3. **Never-OPEN (negative — no setTimeout fallback).** With a mock
   server that never accepts the connection (or the connection that
   stays in CONNECTING), assert `server.nextMessage` does NOT resolve
   to a SESSION_EVENT within a generous window
   (`vi.advanceTimersByTime(5000)` with fake timers). This is the test
   that catches a regression to a `setTimeout`-based send.

A static assertion is also valuable: `grep -L "setTimeout(" App.tsx`
inside the slug-connect closure. The test suite can include a source
inspection check that the literal `setTimeout(...300)` is gone from
the slug-connect path. (Optional; the behavioral test #3 is the
primary guard.)

### What the OTEL story is, and isn't

UI-only change. No new server spans, no new watcher events. The `barrier.wait`
and `lobby.state_transition` spans introduced by 45-2 are unaffected.
The CLAUDE.md OTEL principle applies "to backend fixes that touch a
subsystem" — this is neither backend nor a subsystem decision, it's a
client-side handshake hygiene fix. **No spans required.** (Sebastien's
lie-detector cares about server-side decisions; the WS handshake is a
transport-layer concern below his observability surface.)

### Related sites — leave alone

- `App.tsx:1293–1300` — defensive `setThinking(false)` on OPEN. Already
  effect-based; no change.
- `App.tsx:1307–1332` — re-handshake-on-reconnect effect. Already
  effect-based; uses `prevReadyState` to detect OPEN transitions. **Do
  not consolidate** with the new slug-connect-OPEN effect; the
  `justConnectedRef.current` suppression at `:1315` exists precisely to
  keep these two paths from double-firing on initial connect.
- `App.tsx:856` — `setTimeout(() => setOffline(true), 3000)` — unrelated
  offline detection, not a handshake timer. Leave alone.

## Scope Boundaries

**In scope:**

- Replace the `setTimeout(..., 300)` block at `App.tsx:1243–1260` with a
  pending-payload ref + `useEffect([readyState, ...])` dispatch.
- Add a ref (e.g., `pendingConnectPayloadRef`) to hold the SESSION_EVENT
  payload between `connect()` and the OPEN transition.
- Three new tests in `sidequest-ui/src/__tests__/` (or extending
  `mp-03-event-sync-wiring.test.tsx` if the fixtures align): OPEN-after-
  connect, OPEN-already, never-OPEN.
- Comment update: replace the 300ms-rationale block at `App.tsx:1240–1242`
  with a comment that explains the effect-based dispatch.

**Out of scope:**

- Redesigning the WebSocket reconnection flow. The
  `useWebSocket`/`useGameSocket` hooks are unchanged.
- The re-handshake-on-reconnect effect (`App.tsx:1307–1332`) — its gate
  on `prevReadyState` is already correct; only the *initial* slug-connect
  path is the smell.
- Server-side handshake changes. The server still receives the same
  `SESSION_EVENT{connect, game_slug, ...}` payload at the same logical
  point; only the client-side timing of the send moves.
- Any change to `sendRef` plumbing or `useGameSocket`'s public surface.
- The unrelated 3000ms offline-detection timer at `App.tsx:856`.
- OTEL spans — UI-only fix, no server-side subsystem touched.

## AC Context

1. **The 300ms `setTimeout` in the slug-connect path is removed.**
   - Source-level: `App.tsx:1243–1260` no longer contains a `setTimeout`
     wrapping the `sendRef.current?.(...)` call.
   - The send happens from a `useEffect` keyed on `readyState`, not a
     timer.

2. **SESSION_EVENT{connect} fires on the readyState=OPEN transition.**
   - Test (OPEN-after-connect): mock WS server, mount the app at a
     `/solo/<slug>` route, assert `await server.nextMessage` resolves
     to a `SESSION_EVENT` with `event: "connect"`, `game_slug`,
     `player_name`, `last_seen_seq` populated, **without advancing fake
     timers past 300ms**.
   - Wire-first: the test drives the actual React effect against a real
     mock WebSocket — not a unit test on a `dispatchSessionEvent()`
     helper.

3. **Synchronous-OPEN path also fires.**
   - Test (OPEN-already): if `readyState` is already `OPEN` when the
     effect runs (e.g., StrictMode double-mount, cached socket), the
     SESSION_EVENT fires from the effect's first run. No deadlock, no
     missed dispatch.

4. **No setTimeout fallback re-introduces the smell.**
   - Test (never-OPEN): with a WS that stays in CONNECTING, advance
     fake timers by 5000ms and assert no SESSION_EVENT was sent. This
     test fails today (the 300ms timer would fire and `sendRef.current?.(...)`
     would attempt to send against a non-OPEN socket); after the fix it
     passes because the effect only fires on the OPEN transition.

5. **Existing handshake tests still pass unchanged.**
   - `lobby-start-ws-open.test.tsx`, `mp-03-event-sync-wiring.test.tsx`,
     `chargen-stats-grid-wiring.test.tsx`, and `paused-banner-wiring.test.tsx`
     all consume `await server.nextMessage` for the SESSION_EVENT
     connect payload. Their assertions on payload shape must continue
     to hold — the only change is that the message now arrives via
     effect-driven dispatch rather than via a 300ms timer.
