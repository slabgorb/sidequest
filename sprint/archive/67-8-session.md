---
story_id: "67-8"
jira_key: ""
epic: "67"
workflow: "tdd"
---
# Story 67-8: Eliminate duplicate-socket reconnect loop stranding confrontations in AwaitingConnect (diagnosis-led; AC1/AC2/AC3/AC6 deferred from 67-7)

## Story Details
- **ID:** 67-8
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-server, sidequest-ui

## Story Summary

Epic 67 addresses transport-layer resilience — a socket failure must not make the game feel broken. Playtest 2026-05-28 (coyote_star solo) exposed a critical loop: committing a dogfight beat fired `DICE_THROW` frames that the server rejected with `session.message_rejected_unbound` ×4+ because the session was stranded in `AwaitingConnect` state. A single beat took ~5 rejected attempts plus a full page reload before one roll landed.

Story 67-7 (merged PR #516) delivered only AC5 (telemetry to detect unbound rejections). This story, 67-8, carries the deferred acceptance criteria (AC1/AC2/AC3/AC6) that will eliminate the duplicate-socket / reconnect loop at its root and restore first-attempt rollability mid-confrontation.

## Technical Context

### Root Problem (67-7 Findings)

- **Duplicate sockets:** The logs show "connection open" ×2, two `ws.connection_accepted` / `chargen_gate` cycles per reconnect — the UI page appears to remount repeatedly.
- **Stranded binding:** The `AwaitingConnect`→`Playing` handshake does not complete before the dice frame is sent, causing rejection.
- **Page reload is the workaround:** After a deliberate reload, the handshake completed (`slug_resumed turn=3`, `slug_resume_confrontation_emitted ship_combat`) and the very next Broadside resolved (dice.throw_resolved CritSuccess). **The engine is fine; the transport/session-binding is the block.**

### Two Angles (67-8 must pick one, with diagnosis)

1. **Root cause (preferred):** eliminate the duplicate-socket / repeated `ws.connection_accepted` reconnect cycle. Determine whether the churn is a **UI remount loop** (`sidequest-ui/src/App.tsx` slug-connect effect + ErrorBoundary remount logic, `useWebSocket.ts` socket lifecycle) or a **server session-binding race**. The `window.WebSocket` patch being wiped mid-session is a UI-side clue.
2. **Hardening (secondary):** buffer/retry a beat's action frame across a reconnect until `Playing`, rather than hard-rejecting. **This is explicitly ruled out as the primary path** — buffering belongs to #G3 heavy-hammer WS-teardown territory and risks masking the real bind failure (No Silent Fallbacks).

**AC4 (from 67-7 Architect decision): pursue angle 1 (eliminate the loop), NOT buffer-until-Playing.** Rationale: the guard rejection is correct; the defect is the churn that keeps the session unbound, so the fix must remove the churn, not paper over it.

### Key Constraints

- **No Silent Fallbacks:** if a frame is genuinely unbound, the rejection stays loud; any buffering must be explicit and bounded.
- **Distinction in telemetry:** The AC5 watcher event from 67-7 (`state_transition` / component=`session` / `recovery=session_unbound`) is the instrument to tell genuine-unbound rejection from reconnect churn.
- **Adjacent surfaces:** 59-20 (per-recipient delivery firewall — distinct seam), #G3/#G1 (WS teardown hardening).

## Acceptance Criteria (Deferred from 67-7)

1. **AC1: Root cause identified** — The duplicate-socket / repeated `ws.connection_accepted` cycle is explained (UI remount loop vs server bind race) with log/OTEL evidence captured in the story. *This requires a live repro of the dogfight churn — likely in oq-2 with the playtest scenario's beat commit sequence.*

2. **AC2: No spurious second socket** — A solo confrontation session no longer opens a second socket / re-runs the connect handshake; `AwaitingConnect`→`Playing` completes before action frames are submitted.

3. **AC3: First-attempt roll** — Committing a dogfight beat lands its `DICE_THROW` on the first attempt — no `message_rejected_unbound` loop, no required page reload. **Verify:** drive a beat commit against a freshly-connected session → one roll resolves.

4. **AC6: Regression coverage** — Test coverage for the reconnect/bind path; if reproducible in MP as well as solo, the fix covers both.

### Decision (AC4, from 67-7 Architect)

**Eliminate the loop** (not buffer-until-Playing). The duplicate-socket/remount churn is the root cause; the fix must remove it. The AC5 telemetry from 67-7 is the diagnostic instrument.

## Development Approach (TDD)

**RED phase (TEA):**
- Design failing tests that capture the remount/bind loop and verify a first-attempt roll lands on the first DICE_THROW without rejections.
- AC1 is a process/doc AC (requires live repro) — test the symptom that a fresh session's AwaitingConnect→Playing handshake completes before action frames are submitted.
- AC6 regression coverage: tests that the reconnect path does not re-trigger duplicate-socket opens.

**GREEN phase (Dev):**
- Diagnose the UI remount loop (App.tsx slug-connect effect + ErrorBoundary remount, useWebSocket.ts socket lifecycle) or server bind race via live repro in oq-2.
- Record the AC1 diagnosis in the session file's Delivery Findings.
- Eliminate the duplicate-socket cause.
- Verify that the AC5 telemetry from 67-7 shows zero `session_unbound` rejections in a multi-beat confrontation.
- Land a dogfight beat on the first attempt with zero reloads.

**Verify phase (TEA):**
- Confirm reconnect regression coverage is green.
- Lint + test + simplify checks.

**Review + Spec-check + Reconcile:**
- Review the root-cause fix; Architect verifies all AC1–AC6 are met.
- SM finishes.

## Sm Assessment

**Routing decision:** Hand off to TEA (The Architect) for the RED phase of this phased TDD workflow.

**Why this story, why now:** 67-8 is the highest-impact available story (P1) and the fix-leg of a diagnosis-led pair. I verified via git history before setup that the work is genuinely open — no `67-8` branch and no `67-8` PR exist in either repo, and the sprint YAML status is `backlog`. The merged 67-7 work (PR #516) delivered only AC5 telemetry; the deferred ACs (AC1/AC2/AC3/AC6) — the actual loop elimination — are unstarted. This is real, unduplicated work.

**Scope guardrails for TEA:**
- AC4 is already decided by the 67-7 Architect: **eliminate the duplicate-socket/remount loop**, do NOT buffer-until-Playing. RED tests must target the churn symptom (AwaitingConnect→Playing completes before action frames submit), not a buffering shim.
- AC1 is a live-repro/diagnosis AC — frame the failing test around the observable symptom (first-attempt DICE_THROW lands with zero `session_unbound` rejections), not the internal cause, which Dev pins during GREEN.
- The AC5 watcher event from 67-7 is the diagnostic instrument; reuse it to distinguish genuine-unbound rejection from reconnect churn.
- Two repos in play (server + ui) — the root cause may be UI-side (App.tsx remount + useWebSocket.ts lifecycle) or a server bind race; RED coverage should be ready to land on either side.

**No-Silent-Fallbacks reminder:** any retry/buffer that does sneak in must be explicit and bounded — a genuinely unbound frame must still reject loudly.

**Branches:** `feat/67-8-duplicate-socket-reconnect-loop` cut off `develop` in both repos. No Jira key (Jira skipped per story). No blocking open PRs.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-29T16:42:12Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-29T13:27:05Z | 2026-05-29T13:29:16Z | 2m 11s |
| red | 2026-05-29T13:29:16Z | 2026-05-29T13:38:57Z | 9m 41s |
| green (diagnosis spike) | 2026-05-29T13:38:57Z | 2026-05-29T15:22:59Z | 1h 44m 2s |
| red | 2026-05-29T15:22:59Z | 2026-05-29T15:33:40Z | 10m 41s |
| green | 2026-05-29T15:33:40Z | 2026-05-29T16:09:41Z | 36m 1s |
| spec-check | 2026-05-29T16:09:41Z | 2026-05-29T16:12:00Z | 2m 19s |
| verify | 2026-05-29T16:12:00Z | 2026-05-29T16:18:51Z | 6m 51s |
| review (APPROVED w/ non-blocking findings) | 2026-05-29T16:18:51Z | 2026-05-29T16:30:43Z | 11m 52s |
| green | 2026-05-29T16:30:43Z | 2026-05-29T16:34:08Z | 3m 25s |
| spec-check | 2026-05-29T16:34:08Z | 2026-05-29T16:34:55Z | 47s |
| verify | 2026-05-29T16:34:55Z | 2026-05-29T16:36:29Z | 1m 34s |
| review | 2026-05-29T16:36:29Z | 2026-05-29T16:41:00Z | 4m 31s |
| spec-reconcile | 2026-05-29T16:41:00Z | 2026-05-29T16:42:12Z | 1m 12s |
| finish | 2026-05-29T16:42:12Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation) — AC1 code-trace (partial diagnosis, pre-live-repro)

Static trace of the implicated transport path (not yet confirmed by live repro — see blocking note below):

- **`useWebSocket.createSocket()` orphans the old socket OPEN** — `sidequest-ui/src/hooks/useWebSocket.ts:137-187`. On line 142 it calls `detachHandlers(wsRef.current)` (nulls handlers) but **never calls `.close()`** on the previous socket before opening the new one. On the timer-driven reconnect path the old socket was already closed by `onclose`, so this is benign there. But if `connect()`/`createSocket()` fires while a socket is still live (a remount or a slug-connect/reconnect race), the prior server connection lingers OPEN and unreferenced → a genuine duplicate server-side socket. This matches the 67-7 "connection open ×2" clue.
- **Per-mount connect latch resets on remount** — `App.tsx:1691-1790`. The slug-connect effect is guarded by the `slugConnectFired.current` *ref*, so it fires `connect()` + stages the `SESSION_EVENT{connect}` rebind (`pendingConnectPayloadRef`) exactly once per mount. A full **remount** recreates the ref (→ false) and re-runs the entire connect path — a second `ws.connection_accepted` + `chargen_gate` cycle, matching the 67-7 "two cycles per reconnect" clue.
- **Reconnect DOES re-handshake, but with an async AwaitingConnect window** — `App.tsx:1848-1873` (effect 2) re-sends `SESSION_EVENT{connect}` on a genuine mid-session reconnect. However the new server socket sits in `_State.AwaitingConnect` until the connect handler finishes (pack/world load + event replay). A `DICE_THROW` fired in that window is correctly rejected (`handlers/dice_throw.py:55-66`). The ×4+ repetition implies the dice frame is re-fired while still unbound (dice-overlay retry / re-submit path — NOT yet traced).
- **Ruled out:** the `ErrorBoundary name="Game"` crash path does NOT reopen a socket — `handleGameCrash` (`App.tsx:1260-1269`) only sends `CLIENT_ERROR` over the still-open socket (Story 67-1). So the second socket is not a direct product of a GameBoard render crash.

**Strongest current hypothesis:** a remount (StrictMode dev double-mount, or a key/parent-driven remount during the confrontation overlay) re-runs the slug-connect path, and `createSocket` leaves the prior socket OPEN — yielding two server connections; the freshly-opened one is briefly in `AwaitingConnect`, and a beat-commit `DICE_THROW` racing the rebind handshake is rejected repeatedly. **Two candidate fixes to weigh post-confirmation:** (a) `createSocket` must `.close()` the orphaned socket before replacing it; (b) the connect path must be idempotent across remount so a single session never opens a second socket. Both align with AC4 "eliminate the loop," neither buffers frames.

- **Gap** (blocking): AC1 root cause is **narrowed but not confirmed** — the exact trigger of the second socket (StrictMode-dev vs a real remount vs a slug-connect/reconnect race) and the dice-frame re-fire loop both require a **live repro** to pin from logs/OTEL. The repro needs the full stack running and the coyote_star ship_combat beat-commit sequence driven through the UI. *Found by Dev during implementation.* **Cannot proceed to a confirmed fix or to TEA's targeted RED tests until the live repro disambiguates the trigger.**

### Dev (implementation) — AC1 live-repro result (2026-05-29)

Ran a full Playwright repro against the live stack (server up on :8765 after the `.env` fix; fresh solo `2026-05-29-coyote_star`). Path: chargen → "Yes, And" dogfight trigger ("The screen lights up! Pirates!…") → narrator spun up a `ship_combat` confrontation → committed the **Broadside** strike beat (the playtest's canonical beat).

**Result — the strand did NOT reproduce in clean play:**
- `dice.throw_resolved rolling_player=Smith total=11 outcome=Fail beat_id=broadside` — DICE_THROW landed **first attempt** (server log).
- `ws.connection_accepted` count = **1**; `message_rejected_unbound` count = **0**; no duplicate socket; no `AwaitingConnect` rejection.
- `confrontation.peer_projection_broadcast … encounter_type=ship_combat active=True` — confrontation engaged normally.
- Sole console error = a **font 404** (`Rajdhani-Regular.woff2`), NOT a render crash → the `ErrorBoundary name="Game"` remount path is **not** passively tripping in normal play.

**Conclusion (AC1):** the bug is **churn-gated, not present in the normal beat-commit path.** The strand requires an actual remount/reconnect mid-confrontation; a clean session commits beats first-try with a single socket. This empirically rules out "any ship_combat beat strands" and corroborates the code-trace mechanism (the two defects below), which only manifest when a remount/reconnect occurs. Operator elected (2026-05-29) to accept this code-trace + clean-baseline diagnosis rather than force the churn via a socket bounce.

**Confirmed root-cause defects (the fix targets, AC4 = eliminate the loop):**
1. **`useWebSocket.createSocket()` leaves the orphaned socket OPEN** — `sidequest-ui/src/hooks/useWebSocket.ts:142` detaches handlers but never `.close()`s the prior socket before replacing `wsRef.current`. A remount/connect-race leaves a second live server connection.
2. **Connect path is not idempotent across remount** — `App.tsx:1691-1790` gates the connect+rebind on the per-mount `slugConnectFired` *ref*, so a remount re-runs the whole connect (second `ws.connection_accepted` + `chargen_gate`) and the freshly-opened socket is briefly `AwaitingConnect`, stranding a racing beat `DICE_THROW`.

- **Gap** (non-blocking, separate bug): the ship_combat confrontation edge bars render **`0/1000000 hp`** for both sides (`ConfrontationOverlay`, observed via UI snapshot). Likely an ablative-HP/edge-pool initialization issue for `ship_combat` (ADR-114 surface) — out of scope for 67-8 (transport), but worth a follow-up story. *Found by Dev during implementation.*

### TEA (test design)
- **Gap** (blocking): RED test coverage for AC2/AC3/AC6 cannot be authored before the AC1 root cause is pinned by a live repro. Affects `sidequest-server/tests/` and `sidequest-ui/src/**/__tests__/` (the reconnect/bind regression tests must be written against the confirmed mechanism, not a guess). *Found by TEA during test design.* **Dev must, in the diagnosis spike: (1) live-repro the dogfight churn (oq-2, playtest beat-commit sequence), (2) pin whether the duplicate `ws.connection_accepted` cycle originates UI-side (App.tsx remount + useWebSocket.ts lifecycle) or server-side (session bind race), capturing log/OTEL evidence, (3) record the AC1 diagnosis here, then (4) hand back to TEA so RED tests are authored at the correct level before the GREEN fix is accepted.**
- **Improvement** (non-blocking): The server already emits `presence.multi_socket_attach` (when `live_socket_count > 1`) and `presence.disconnect_skipped` (ref-counted presence) in `sidequest-server/sidequest/server/session_room.py` (~:404-540). These spans, alongside the 67-7 `session_unbound` watcher event, are ready-made diagnostic instruments for the live repro — assert against them rather than adding new telemetry. *Found by TEA during test design.*
- **Gap** (blocking): Defect #2 (App `slugConnectFired` per-mount ref re-runs the connect handshake on remount) has NO failing unit test in RED — its harmful manifestation depends on the unpinned remount trigger, so a unit test would encode a guessed mechanism. Affects `sidequest-ui/src/App.tsx` (~:1691-1790). GREEN must close this with an OTEL acceptance gate: **zero `session_unbound` rejections + no `presence.multi_socket_attach` across a multi-beat live confrontation**. The Verify phase must confirm that OTEL evidence, not just the green unit suite. *Found by TEA during test design.* See the matching Design Deviation. **Honors AC4 (eliminate the loop) and No-Silent-Fallbacks — the GREEN gate is the trigger-independent observable for defect #2.**
- **Improvement** (non-blocking): `useWebSocket.connect()` documents "Open a connection (no-op if already connected)" (`useWebSocket.ts:46`) but the implementation unconditionally calls `createSocket()` — a doc/impl contract violation that is the proximate cause of defect #1. Whichever fix Dev chooses, the doc comment and the behavior should end up consistent. *Found by TEA during test design.* **Resolved in GREEN (`6a73615`): connect() now early-returns when OPEN.**

### Dev (green implementation)
- **Gap** (non-blocking): Layer 2 — the WebSocket connection + slug-connect handshake are owned in `AppInner`, inside per-route `LobbyRoot` (the shared `element` of three `<Route>`s) under `<StrictMode>`, so any route transition, `#/dashboard` hash toggle, or StrictMode double-mount remounts the socket-owning tree and re-runs the full connect handshake (second `ws.connection_accepted` + `chargen_gate`). Affects `sidequest-ui/src/App.tsx` (~:2298-2320 routing, :1691-1790 slug-connect, :1198 socket) — the correct fix hoists the connection (and the handshake latch) to a stable owner **above `<Routes>`** so it fires once per page-session and reconnects are driven only by genuine socket drops → server resume. **Deferred to a follow-up story** (own RED tests + review) per Operator direction; Layers 1+3 already make the residual re-handshake harmless (no duplicate socket, no commit during AwaitingConnect). *Found by Dev during implementation.*
- **Improvement** (non-blocking): ship_combat confrontation edge bars render `0/1000000 hp` (already logged above under the AC1 live-repro Dev finding) — ablative-HP init for `ship_combat` (ADR-114), out of scope for 67-8. Carry into the same or an adjacent follow-up.

### TEA (test verification)
- **Question** (non-blocking): The AC3 live-OTEL acceptance (`session_unbound`=0 + no `presence.multi_socket_attach` across a multi-beat confrontation) was NOT run on the live stack during verify, because the strand is churn-gated — a clean-baseline run shows zero rejections even on pre-fix code, so it cannot distinguish fixed-from-unfixed, and forcing the churn was declined during diagnosis. Affects nothing in code; it is an acceptance observable. **Recommend validating it in the next live playtest** (the venue where the bug surfaced) rather than a synthetic verify run. Static verify (RED→GREEN invariants, gate suites, tsc, 1663 tests) passed. *Found by TEA during test verification.* **Operator decision point: run a pre-merge playtest, or accept on static evidence + validate at next playtest.**

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Diagnosis spike completed inside green; routing back to red for TEA RED authoring**
  - Spec source: session "Notes for Next Agent (Dev — Agent Smith)" step 5; TEA blocking finding under Delivery Findings
  - Spec text: "Hand back to TEA … so I author targeted RED tests (AC2/AC3/AC6) at the level the mechanism demands — *before* you implement the GREEN fix."
  - Implementation: Did NOT implement the GREEN fix. Confirmed the live-repro + code-trace diagnosis (AC1, recorded in Delivery Findings, Operator-accepted 2026-05-29), then moved the workflow phase green→red and handed to TEA. (`pf workflow fix-phase` guards against backward transitions, so the session `**Phase:**` line + Phase History were repaired directly — the only mechanism for the detour's return leg.) GREEN implementation resumes only after TEA's targeted RED tests exist.
  - Rationale: The diagnosis-first detour was designed precisely to return to TEA once the mechanism was pinned. AC1 is now pinned (two confirmed UI-side defects); implementing GREEN before RED would violate the diagnosis-first agreement and leave TEA's blocking gap unresolved. Operator confirmed "hand back to TEA for RED" (2026-05-29).
  - Severity: major (deliberate backward phase transition; documented detour, not a skipped gate)
  - Forward impact: TEA authors RED tests against the confirmed mechanism (orphaned-socket-not-closed; non-idempotent connect across remount), then returns to Dev for GREEN.
- **AC4 decision confirmed by diagnosis — eliminate the loop, no buffering**
  - Spec source: session AC4 (from 67-7 Architect); context-story-67-8.md "Two Angles"
  - Spec text: "AC4 … pursue angle 1 (eliminate the loop), NOT buffer-until-Playing."
  - Implementation: The two confirmed root-cause defects are addressed by (a) `createSocket` closing the orphaned socket before replacing it and (b) making the connect path idempotent across remount. Both remove the churn at its source; neither buffers or retries an unbound frame. The unbound-frame rejection stays loud (No Silent Fallbacks).
  - Rationale: Diagnosis corroborates that the churn (duplicate socket + remount re-connect) is the root cause, not the guard rejection — so AC4's "eliminate the loop" path is the correct, confirmed direction.
  - Severity: minor (confirmation of an existing locked decision; no change in approach)
  - Forward impact: Constrains the GREEN fix to loop-elimination; any buffering would be a regression against AC4.
- **GREEN fix is three-layered; Layers 1+3 shipped, Layer 2 (connection hoist) deferred to a follow-up**
  - Spec source: session AC2/AC3/AC6; Operator direction 2026-05-29 (approved the full three-layer analysis, "go")
  - Spec text: AC2 "no longer opens a second socket / re-runs the connect handshake; AwaitingConnect→Playing completes before action frames are submitted"; AC3 "first-attempt roll".
  - Implementation: Full root-cause analysis found three layers. **Layer 1 (transport, RED-tested):** `useWebSocket.createSocket` now closes a still-live prior socket before replacing it, and `connect()` honors its documented no-op-when-OPEN contract — no duplicate/orphaned sockets (`6a73615`). **Layer 3 (protocol, Dev-tested):** a server-authoritative `sessionBound` signal gates beat-commit via the pure `beatDispatchBlockReason()` helper, so a `DICE_THROW` is never issued into an OPEN-but-unbound socket (`366466a`). **Layer 2 (architecture, DEFERRED):** the socket + connect-handshake live in `AppInner` inside per-route `LobbyRoot` under StrictMode, so route/dashboard/StrictMode remounts re-run the handshake; the correct fix hoists the connection above `<Routes>`. Deferred to a follow-up story (logged as a delivery finding).
  - Rationale: Layers 1+3 make the strand impossible and satisfy the player-facing ACs — AC2's "AwaitingConnect→Playing completes before action frames are submitted" (Layer 3 refuses commits until bound) and AC3 first-attempt roll (no frame into an unbound socket). The AC2 sub-clause "no longer re-runs the connect handshake" is satisfied *behaviorally* (the re-handshake is now harmless: Layer 1 prevents duplicate sockets, Layer 3 blocks commits during the AwaitingConnect window) rather than by eliminating the re-handshake itself, which is Layer 2. A 2300-line-`App.tsx` connection-ownership refactor warrants its own RED tests + review rather than being crammed, untested, into this green phase (minimalist discipline; risk containment). Operator approved this split direction.
  - Severity: major (GREEN added Layer 3 behavior beyond TEA's Layer-1 RED tests — Dev authored the Layer-3 tests; and one AC2 sub-clause is met behaviorally, not by churn removal, pending Layer 2)
  - Forward impact: Verify (TEA) should confirm Layers 1+3 via the unit suites AND the OTEL acceptance observable (session_unbound=0 + no presence.multi_socket_attach across a multi-beat live confrontation). Layer 2 follow-up removes the residual (now-harmless) churn at its architectural root; until then a spurious remount still re-handshakes but no longer strands a beat.
- **Post-review cleanup amend (review→green→re-review) addressing the 5 Reviewer findings**
  - Spec source: Reviewer Assessment (this session); Operator direction 2026-05-29 (chose option (a) — quick Dev amend)
  - Spec text: Reviewer findings — `[MEDIUM] handleDiceThrow does not re-check sessionBound`; `[SEC/LOW] App.tsx:1445 unreachable silent return`; `[RULE/LOW] as any` + `instances[0]!` test hygiene.
  - Implementation: (1) `handleDiceThrow` now gates on `sessionBound` at send-time — refuses + resets dice state if the session unbound during physics (closes the AC3 mid-physics race; commit `4d516b4`). (2) The post-gate `if (!beat)` branch now `console.error`s the invariant violation instead of silent return (No Silent Fallbacks). (3) Test `as any`→`as unknown as typeof WebSocket`; three `instances[0]!` now preceded by `toHaveLength(1)`. (4) New wiring test pins the handleDiceThrow gate. Phase moved review→green for the amend (session-file phase repair, as the diagnosis-first detour did) and re-exits through spec-check/verify/review.
  - Rationale: The findings were non-blocking (no Critical/High) but rule-matching; the Operator elected to deliver the genuinely-complete fix rather than ship known nits. handleDiceThrow's gate is the substantive one — it makes AC3 robust even in the mid-physics unbind race the beat-select gate didn't cover.
  - Severity: minor (review-driven cleanup of non-blocking findings; no change to the core Layer 1/3 approach)
  - Forward impact: handleDiceThrow gate slightly overlaps the Layer 2 follow-up's concerns but is independently correct. Re-review (Merovingian) should confirm the 4 findings are resolved. Full suite 1664/1664 green.

### TEA (test design)
- **RED tests deferred to post-diagnosis (diagnosis-first spike)**
  - Spec source: context-story-67-8.md, AC1 + AC Context; session AC4 decision
  - Spec text: "AC1 — Root cause identified ... requires a live repro of the dogfight churn (UI remount loop vs server bind race)"; AC2/AC3/AC6 are symptom-level invariants whose *test level* depends on the mechanism.
  - Implementation: TEA wrote NO failing tests in this RED phase. The phase hands directly to Dev for a live-repro diagnosis spike to pin the mechanism, after which RED tests are authored against the known cause.
  - Rationale: The mechanism is genuinely unknown (UI remount vs server bind race). The 67-7 Architect explicitly recorded that AC2/AC3/AC6 reconnect-loop coverage is "gated on that diagnosis rather than fabricated" (`tests/server/test_unbound_rejection_telemetry_67_7.py` lines 29-36). Authoring unit tests now would either pass vacuously (wrong level — e.g. a server idempotent-connect test that's GREEN because the churn is UI-side; a UI in-hook double-connect guard that misses a full-remount cause) or hard-code a guessed mechanism — violating No-Stubbing and the meaningful-assertion rule. Operator confirmed the diagnose-first spike (2026-05-29).
  - Severity: major (deviates from standard red-first TDD ordering)
  - Forward impact: After Dev records the AC1 root-cause diagnosis, work returns to TEA to author targeted RED tests (AC2/AC3/AC6) at the level the mechanism demands, then back to Dev for GREEN. This is a deliberate detour, not a skipped gate.
- **RED tests authored at the socket-lifecycle layer (useWebSocket), not App's `slugConnectFired` latch; App-remount manifestation deferred to GREEN OTEL**
  - Spec source: context-story-67-8.md AC2/AC3/AC6; session Delivery Findings (Dev AC1 diagnosis, two confirmed defects)
  - Spec text: "AC2 — No spurious second socket … `AwaitingConnect`→`Playing` completes before action frames are submitted"; "AC6 — Test coverage for the reconnect/bind path."
  - Implementation: Authored `sidequest-ui/src/hooks/__tests__/useWebSocket-67-8-duplicate-socket.test.ts` — four fix-agnostic invariants at the layer that owns socket lifecycle. The two **defect #1** invariants (server never sees >1 live socket across a connect-while-OPEN; the prior socket is never left OPEN-but-orphaned) fail RED. AC3 (send-only-when-OPEN) and AC6 (genuine reconnect → exactly one live socket) pass as green guardrails. **Defect #2** (App `slugConnectFired` is a per-mount ref that re-runs the connect handshake on remount) is NOT unit-tested in RED.
  - Rationale: (1) Defect #1 is the confirmed, trigger-independent root cause of the duplicate *server* socket — testing the AC2 invariant at the hook layer is fix-agnostic (passes for either no-op-when-OPEN or close-and-replace) and avoids over-constraining Dev's fix shape. (2) Defect #2's *harmful* manifestation depends on the exact remount trigger, which the AC1 diagnosis explicitly left unpinned (Operator accepted the code-trace + clean-baseline rather than force the churn). A unit test reproducing it would have to PICK a trigger (StrictMode-dev vs real remount vs slug-connect/reconnect race) — encoding a guessed mechanism, the precise vacuous/wrong-level trap that justified the diagnosis-first deferral. Its trigger-independent observable is verified end-to-end in GREEN via OTEL: **zero `session_unbound` rejections across a multi-beat confrontation** (plus `presence.multi_socket_attach` never firing) — the instruments TEA flagged from `session_room.py`.
  - Severity: major (a confirmed defect — #2 — has no failing unit test in RED; covered by a GREEN acceptance gate instead)
  - Forward impact: Dev's GREEN must (a) make the hook satisfy the two failing AC2 invariants, AND (b) verify the App-level `slugConnectFired` remount path no longer re-runs the connect handshake, evidenced by OTEL `session_unbound`=0 + no `presence.multi_socket_attach` in a multi-beat live confrontation. The Verify phase (TEA) must confirm that OTEL evidence, not just the unit suite.
- **Verify-phase: live-OTEL acceptance deferred to the next playtest (not run synthetically)**
  - Spec source: own RED-phase forward-impact note (above) + Architect spec-check watch-item 1
  - Spec text: "The Verify phase (TEA) must confirm that OTEL evidence [`session_unbound`=0 + no `presence.multi_socket_attach` across a multi-beat live confrontation], not just the unit suite."
  - Implementation: Verify confirmed the static evidence (RED→GREEN invariants, beatDispatch + wiring suites, `tsc` clean, 1663 tests green, simplify clean) but did NOT run the live-stack OTEL acceptance.
  - Rationale: The strand is churn-gated — a clean-baseline multi-beat run emits zero `session_unbound` even on pre-fix code (Dev's 2026-05-29 live repro proved this), so a synthetic happy-path OTEL run cannot distinguish fixed-from-unfixed; and forcing the churn (socket bounce) was explicitly declined by the Operator during diagnosis. The honest validation venue is a real playtest, where the original strand surfaced.
  - Severity: minor (acceptance-observable validation deferred to playtest; the code-level ACs are covered by passing tests + review, and the live check cannot add signal on a clean baseline)
  - Forward impact: The next live playtest should confirm `session_unbound`=0 + no `presence.multi_socket_attach` across a multi-beat confrontation. Recorded as a non-blocking TEA delivery finding (Operator decision point: pre-merge playtest vs. accept-on-static + validate-at-next-playtest).

### Reviewer (audit)
- **Dev: diagnosis spike routed back to red** → ✓ ACCEPTED by Reviewer: correct application of the diagnosis-first detour; phase tracking repaired honestly.
- **Dev: AC4 confirmed — eliminate the loop, no buffering** → ✓ ACCEPTED by Reviewer: code confirms it — Layer 3 refuses (no queue); No Silent Fallbacks intact.
- **Dev: three-layered fix, Layers 1+3 shipped, Layer 2 deferred** → ✓ ACCEPTED by Reviewer: the AC2 "no re-run of the connect handshake" clause is met behaviorally (Layer 1 = no dup socket; Layer 3 = no commit while unbound), and the architectural hoist is legitimately follow-up-sized. Operator-sanctioned. Sound.
- **TEA: RED tests at the socket-lifecycle layer; defect #2 deferred to OTEL** → ✓ ACCEPTED by Reviewer: testing the trigger-independent invariant rather than guessing an unpinned remount trigger is the correct call; the live-OTEL gate is the right venue for defect #2.
- **TEA: live-OTEL acceptance deferred to playtest** → ✓ ACCEPTED by Reviewer: justified — a clean-baseline run can't distinguish fixed-from-unfixed (churn-gated), and forcing churn was declined. Flagged to the Operator as a decision point, which is the honest disposition.
- No undocumented spec deviations found beyond those already logged. The handleDiceThrow `sessionBound` gap and the `App.tsx:1445` silent branch are code-quality findings (recorded in the Reviewer Assessment), not spec deviations.
- **Dev: post-review cleanup amend (review→green→re-review)** → ✓ ACCEPTED by Reviewer (2nd pass): the amend resolved all 5 of my findings and the re-review subagents (preflight/security/rule-checker) confirmed clean with no new issues. The handleDiceThrow gate (the Medium) is now closed — AC3 is robust across the full roll lifecycle.

### Architect (reconcile)

**Manifest audit — all in-flight deviations verified accurate, 6-field, and self-contained:**

- **Verified existing entries (Dev ×4, TEA ×3):** spec sources are real files (`sprint/context/context-story-67-8.md` present; `.pennyfarthing/gates/lang-review/typescript.md` present; session AC4/AC2 quoted accurately); implementation descriptions match the shipped code (`useWebSocket.ts` close-orphan + connect no-op; `App.tsx` `sessionBound` gate on `handleBeatSelect` *and* `handleDiceThrow`; `beatDispatch.ts` helper); forward-impact statements are accurate. No corrections needed.
- **No additional deviations found.** The cleanup amend (`4d516b4`) closed the only substantive code-quality finding (handleDiceThrow gate); the remaining review findings were test-hygiene/loud-logging, not spec deviations.

**AC accountability (definitive, for the boss):**

| AC | Status | Disposition |
|----|--------|-------------|
| AC1 Root cause identified | **DONE** | Code-trace + live-repro recorded in Delivery Findings; Operator-accepted 2026-05-29. Two defects pinned (orphaned socket; non-idempotent remount connect). |
| AC2 No spurious second socket | **DONE (split)** | Socket-duplication + "FSM Playing before action frames" clauses met by Layers 1+3. The "does not re-run the connect handshake" sub-clause is **DEFERRED** to the Layer-2 connection-hoist follow-up (Option D, Operator-sanctioned) — residual re-handshake is harmless (no dup socket, no commit while unbound). |
| AC3 First-attempt roll | **DONE** | Layer 3 gates beat-commit at both roll-start (`handleBeatSelect`) and roll-send (`handleDiceThrow`) on `sessionBound`. Live-OTEL confirmation of zero `session_unbound` is **deferred to the next playtest** (non-blocking; churn-gated so a synthetic run adds no signal). |
| AC4 Eliminate the loop, no buffer | **DONE** | All gates refuse-and-retry; nothing queues a frame. No Silent Fallbacks intact. |
| AC6 Regression coverage | **DONE** | `useWebSocket-67-8` invariants (RED→GREEN) + `beatDispatch` unit suite + wiring suite + teardown/isReconnecting regression. Shared-hook fix covers solo and MP. |

**Two carried follow-ups (documented, non-blocking for 67-8):**
1. **Layer-2 connection hoist** — move the WebSocket + slug-connect handshake above `<Routes>` so route/dashboard/StrictMode remounts cannot re-run the handshake (eliminates the residual churn at its architectural root). Own RED/review cycle. *(Dev delivery finding.)*
2. **Live-OTEL playtest validation** — confirm `session_unbound`=0 + no `presence.multi_socket_attach` across a multi-beat live confrontation. *(TEA delivery finding; Operator decision point.)*
3. (Adjacent) ship_combat edge bars render `0/1000000 hp` — ablative-HP init (ADR-114), out of scope. *(Dev delivery finding.)*

**Reconcile decision:** Deviation manifest is complete and accurate. Proceed to SM finish.

## Notes for Next Agent (TEA)

**67-7 Context (for reference):**
- AC5 (telemetry) was delivered in PR #516 — the `_emit_unbound_rejection_event` helper and watcher events are already live in `develop`.
- The three handlers that guard on Playing state (`dice_throw.py`, `player_action.py`, `orbital_intent.py`) already emit the `session_unbound` watcher event.
- Server-side binding and rejection logic is sound — the block is transport-layer churn (duplicate sockets / remount loop).

**67-8 Scope (this story):**
- Use the AC5 telemetry from 67-7 as the diagnostic lens into the remount/bind loop.
- Live repro in oq-2 is the practical path to pinning whether the churn is UI-side (App.tsx + useWebSocket.ts remount/reconnect) or server-side (bind race / FSM timing).
- Once root cause is identified and fixed, verify first-attempt rolls land in confrontations with zero rejected frames.
- Record the AC1 diagnosis in Delivery Findings and AC4 decision confirmation in Design Deviations.

## TEA Assessment (SUPERSEDED — diagnosis-deferral phase; see "TEA Assessment — RED Phase (post-diagnosis)" at end of file)

**Tests Required:** Deferred (diagnosis-gated) — NO RED tests written this phase.
**Reason:** 67-8 is diagnosis-led. AC1 requires a live repro to pin the root cause (UI remount loop vs server bind race); AC2/AC3/AC6 are symptom-level invariants whose correct *test level* is determined by that mechanism. The 67-7 Architect explicitly recorded that this reconnect-loop coverage is "gated on that diagnosis rather than fabricated" (`tests/server/test_unbound_rejection_telemetry_67_7.py` lines 29-36). Fabricating unit tests now would be vacuous (wrong level) or encode a guessed mechanism — both violate No-Stubbing and the meaningful-assertion rule. Operator confirmed the diagnose-first spike (2026-05-29).

**Test Files:** none (deferred to post-diagnosis)
**Tests Written:** 0 — RED authoring deferred per the diagnosis-first decision.
**Status:** RED phase exits via diagnosis-first detour (documented deviation), not via failing tests.

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| (python/typescript lang-review) | Deferred — test rubric applies once the mechanism is known and RED tests are authored | pending diagnosis |

**Rules checked:** 0 of N applicable — rule-enforcement tests are authored alongside the AC tests, post-diagnosis.
**Self-check:** No tests written, so no vacuous assertions introduced.

**Handoff:** To Dev (Agent Smith) for the live-repro diagnosis spike. **Diagnosis spike mandate** — see "Notes for Next Agent (Dev)" below.

## Notes for Next Agent (Dev — Agent Smith)

**Your phase is a diagnosis spike, not a blind fix. In order:**

1. **Live-repro the churn.** Use oq-2 with the coyote_star / ship_combat dogfight beat-commit sequence from Playtest 2026-05-28. Reproduce the `session.message_rejected_unbound` ×4+ loop in `AwaitingConnect`.
2. **Pin the root cause.** Determine whether the duplicate `ws.connection_accepted` cycle originates:
   - **UI-side** — `sidequest-ui/src/App.tsx` slug-connect effect + `ErrorBoundary name="Game"` (~:2019) remount, `hooks/useWebSocket.ts` onclose/reconnect (:177-186) / `detachHandlers` (:129-135), `hooks/useGameSocket.ts`. The wiped `window.WebSocket` patch is a UI clue.
   - **Server-side** — `sidequest-server/sidequest/handlers/connect.py` (AwaitingConnect→Playing transition, ~:1073-1270) and `server/session_room.py` ref-counted `connect`/`disconnect` (~:404-540).
3. **Capture evidence.** Use the existing instruments — the 67-7 `session_unbound` watcher event, plus `presence.multi_socket_attach` / `presence.disconnect_skipped` spans in `session_room.py`. Do not add new telemetry to diagnose.
4. **Record the AC1 diagnosis** in `## Delivery Findings` under a `### Dev` subheading, with the mechanism and evidence.
5. **Hand back to TEA** (re-run `/pf-tea` or route via SM) so I author targeted RED tests (AC2/AC3/AC6) at the level the mechanism demands — *before* you implement the GREEN fix.

**Hard constraints:**
- AC4 is locked: **eliminate the loop**, do NOT buffer-until-Playing. The unbound-frame rejection is correct; remove the churn that keeps the session unbound.
- No Silent Fallbacks: a genuinely unbound frame must still reject loudly.
- OTEL: the fix's success is observable as **zero `session_unbound` rejections** across a multi-beat confrontation.

## TEA Assessment — RED Phase (post-diagnosis, 2026-05-29)

**Tests Required:** Yes — authored post-diagnosis against the confirmed mechanism (AC1, Operator-accepted).
**Reason:** The diagnosis-first detour is resolved. AC1 pinned the root cause to the socket-lifecycle layer (defect #1: `createSocket` orphans the live socket OPEN; `connect()` violates its documented no-op-when-connected contract). RED tests now exist at that confirmed level.

**Test Files:**
- `sidequest-ui/src/hooks/__tests__/useWebSocket-67-8-duplicate-socket.test.ts` — 4 tests, fix-agnostic socket-lifecycle invariants.

**Tests Written:** 4 covering AC2/AC3/AC6.
- **AC2** — "re-firing connect() while a socket is already OPEN never leaves two live sockets" → **FAILING (RED)**: expected 1 live socket, received 2.
- **AC2** — "connect() while OPEN does not orphan the prior socket in a live state" → **FAILING (RED)**: `firstSocket.close()` never called.
- **AC3** — "send() never transmits on a socket that is not OPEN (no frame fired into AwaitingConnect)" → PASSING (green guardrail — client-side half of first-attempt-roll; the duplicate-socket invariant is the other half).
- **AC6** — "a genuine mid-session reconnect still yields exactly one live socket" → PASSING (green guardrail — fix must not break legitimate reconnect).

**Status:** RED — 2 failing (AC2 root-cause invariants), 2 passing (AC3/AC6 guardrails). No compile/import/type errors. Verified via `testing-runner` (exit 1).

### Rule Coverage (TypeScript lang-review — `.pennyfarthing/gates/lang-review/typescript.md`)

| Rule | Test(s) / How covered | Status |
|------|------------------------|--------|
| #6 React/JSX (effect / socket lifecycle correctness) | The 4 invariants exercise the hook's connect/createSocket/reconnect effects via `renderHook` + a `MockWebSocket`; the fix must keep effect/teardown behavior correct (complements the existing `useWebSocket-teardown.test.ts` regression suite) | failing (AC2) / passing (AC3, AC6) |
| #8 Test quality — meaningful assertions | Every test asserts concrete state (`liveSocketCount()` equality, `close` call count, `send` call count, `readyState`); no `let _ =`, no `assert(true)`, no always-None checks | pass (self-check) |
| #8 Test quality — no `as any` to force types | Only the sanctioned `globalThis.WebSocket = MockWebSocket as any` global stub (eslint-disabled, same pattern as the existing teardown test); no `as any` in assertions; mock shape matches the WebSocket surface the hook uses | pass |
| #1 Type-safety escapes | No new `@ts-ignore` / double-casts / unsafe `!` introduced in the test | pass |

**Rules checked:** 3 of the applicable lang-review checks have explicit coverage/self-check (#1, #6, #8). The remaining checks (#2–#5, #7, #9–#13) are not applicable to a transport-layer regression test (no new enums, generics, async API boundaries, build config, or input-validation surface in the test).
**Self-check:** 0 vacuous assertions — every test asserts a concrete value; reviewed against the meaningful-assertion rule.

**Coverage boundary (see Design Deviation):** Defect #2 (App `slugConnectFired` per-mount ref) is intentionally NOT unit-tested in RED — its harmful manifestation depends on the unpinned remount trigger, so a unit test would encode a guessed mechanism (the trap that justified the diagnosis-first deferral). It is gated in GREEN via OTEL: zero `session_unbound` + no `presence.multi_socket_attach` across a multi-beat live confrontation.

**Handoff:** To Dev (Agent Smith) for GREEN.

## Notes for Next Agent (Dev — Agent Smith) — GREEN Phase

The diagnosis-first detour is closed; RED tests now exist. Make them green:

1. **Satisfy the 2 failing AC2 invariants** in `sidequest-ui/src/hooks/useWebSocket.ts`. The contract-correct, fix-agnostic target: a `connect()` (or any `createSocket()` reached while a socket is still live) must never leave two server-visible (OPEN) sockets, and must never leave the prior socket OPEN-but-orphaned. Honor the documented `connect()` contract ("no-op if already connected", line 46) — either no-op when OPEN, or close-and-replace. **Do NOT buffer frames (AC4).** The tests pass for either valid shape.
2. **Close the defect-#2 coverage gap in GREEN** (no unit test exists by design). Make the App connect path (`App.tsx` ~:1691-1790, `slugConnectFired`) idempotent so a remount does not re-run the connect handshake, and **prove it with OTEL**: a multi-beat live confrontation shows **zero `session_unbound` rejections** and **no `presence.multi_socket_attach`**. Reuse the 67-7 `session_unbound` watcher event + `session_room.py` presence spans — do not add new telemetry.
3. **Keep the green guardrails green:** AC3 (send-only-when-OPEN) and AC6 (genuine reconnect → one live socket) must still pass. Also keep `useWebSocket-teardown.test.ts` green (the 2026-04-11 OTEL-dupe regression suite shares this code path).
4. **Run the full UI suite**, not just the new file — the hook is shared by `useGameSocket` and `useWatcherSocket`.

**Hard constraints (unchanged):** AC4 locked — eliminate the loop, never buffer. No Silent Fallbacks — a genuinely unbound frame still rejects loudly. The OTEL `session_unbound`=0 across a multi-beat confrontation is the acceptance observable.

## Dev Assessment — GREEN Phase (2026-05-29)

**Implementation Complete:** Yes (Layers 1+3; Layer 2 deferred to a follow-up — see Design Deviation + Delivery Finding).

**Files Changed (`sidequest-ui`, branch `feat/67-8-duplicate-socket-reconnect-loop`):**
- `src/hooks/useWebSocket.ts` — Layer 1: `createSocket()` closes a still-live prior socket before replacing it; `connect()` honors its documented no-op-when-OPEN contract. (`6a73615`)
- `src/lib/beatDispatch.ts` (new) — Layer 3: pure `beatDispatchBlockReason()` beat-commit gate (thinking / no-confrontation / unknown-beat / **session_unbound**). (`366466a`)
- `src/App.tsx` — Layer 3: `sessionBound` state (set on connected/ready; reset on non-OPEN readyState and on session_unbound); `handleBeatSelect` routed through the gate. (`366466a`)

**Tests:**
- RED→GREEN (Layer 1): `src/hooks/__tests__/useWebSocket-67-8-duplicate-socket.test.ts` — 4/4 green (was 2 failing).
- New (Layer 3): `src/lib/__tests__/beatDispatch.test.ts` (7) + `src/__tests__/beat-commit-session-bound-wiring-67-8.test.tsx` (6).
- Regression: `useWebSocket-teardown` + `useWebSocket-isReconnecting` green; **full UI suite 1663/1663 green**. ESLint clean on all changed files (2 pre-existing `App.tsx` warnings at :1334/:1904, untouched by this story).

**What's covered vs deferred:**
- **AC2** (no spurious second socket / handshake completes before action frames) — Layer 1 (no duplicate/orphan socket) + Layer 3 (no commit until bound). The "no longer re-runs the connect handshake" sub-clause is satisfied *behaviorally* pending Layer 2.
- **AC3** (first-attempt roll) — Layer 3 guarantees a beat is only committed once the session is bound → lands first try.
- **AC6** (regression coverage) — Layer 1 invariants + Layer 3 gate suites + the teardown/isReconnecting suites.
- **Layer 2** (connection hoist above `<Routes>`) — deferred; residual re-handshake is now harmless.

**OTEL acceptance (for Verify):** Not yet exercised on the live stack — TEA Verify should confirm `session_unbound`=0 and no `presence.multi_socket_attach` across a multi-beat live confrontation (the trigger-independent observable for the churn). No new telemetry added (reuses 67-7 `session_unbound` + `session_room.py` presence spans), per the OTEL principle — this is a UI fix whose success is observed via existing server spans.

**Branch:** `feat/67-8-duplicate-socket-reconnect-loop` (commits `d997e7a` RED, `6a73615` Layer 1, `366466a` Layer 3) — pushed to `origin`.

**Handoff:** To next phase (spec-check / verify).

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (sanctioned — one Major deferral, Operator-approved).
**Mismatches Found:** 1 (plus 3 watch-items handed to Verify).
**Structural gate:** `gates/spec-check` PASS — AC coverage present in Dev Assessment, implementation marked complete, TEA + Dev deviation subsections well-formed.

**Mismatch 1 — AC2 "does not re-run the connect handshake" not eliminated** (Missing in code — Architectural, **Major**)
- Spec (context-story-67-8.md, AC2): "a solo confrontation session does not open a second socket **or re-run the connect handshake**; the FSM reaches `Playing` before any action frame is accepted."
- Code: Layer 1 eliminates the second/orphaned socket; Layer 3 ensures no action frame is submitted before the session is bound (FSM-Playing clause met). The connect handshake **can still re-run** on a spurious remount because the socket + handshake are owned in a remount-prone position (`AppInner` inside per-route `LobbyRoot` under StrictMode) — Layer 2, deferred.
- Recommendation: **D — Defer.** Rationale: the Operator explicitly approved the three-layer split (2026-05-29); the player-facing harm (the strand) is fully eliminated by Layers 1+3 (no duplicate socket; no commit during an `AwaitingConnect` window), so the residual re-handshake is benign. Layer 2 (hoist the connection above `<Routes>`) is a 2300-line-`App.tsx` refactor that warrants its own RED/review cycle — logged as a Dev delivery finding (follow-up story). This is a known, documented deviation with a plan, not silent drift.

**AC-by-AC alignment:**
- **AC1** (root cause identified) — Aligned. Code-trace + live-repro recorded in Delivery Findings, Operator-accepted; two defects pinned.
- **AC2** (no spurious second socket; FSM Playing before frames) — Aligned on the socket + frame-gating clauses (Layers 1+3); handshake-re-run clause deferred (Mismatch 1). Edge "don't over-correct into never-reconnect" — **satisfied**: `connect()` no-ops only when `readyState===OPEN`, so a genuine reconnect after a real close still fires exactly once (proven by the AC6 reconnect test).
- **AC3** (first-attempt roll) — Aligned in code: Layer 3 refuses a beat-commit until the session is bound, so the `DICE_THROW` lands first try. The "zero `session_unbound`" **live** observable is delegated to Verify.
- **AC4** (eliminate the loop, no buffer) — Aligned. Layer 3 refuses-and-retries; nothing queues a frame. No-Silent-Fallbacks intact (server still rejects a genuine unbound frame).
- **AC6** (regression coverage) — Aligned. RED→GREEN Layer-1 invariants + Layer-3 gate suites + teardown/isReconnecting regression. Multi-socket edge: `createSocket` only closes the prior socket **within one hook instance**; legitimate same-player multi-socket presence (separate tabs/devices = separate instances, server ref-counted) is not regressed.

**Watch-items for Verify (TEA):**
1. **OTEL acceptance** — drive a multi-beat live confrontation and confirm `session_unbound`=0 and no `presence.multi_socket_attach` (the trigger-independent observable for the churn). Not yet exercised on the live stack.
2. **No false-block** — confirm the `sessionBound` gate does not refuse a legitimate beat in the happy path (sessionBound must be `true` throughout normal bound play).
3. **Multi-socket presence regression** — confirm closing the orphan in `createSocket` does not strand a legitimate same-player multi-socket session (AC6 edge).

**Decision:** **Proceed to verify.** The single Major mismatch is an Operator-sanctioned, documented deferral (Option D), not a code defect requiring hand-back. No Option-B fixes required.

## TEA Assessment — Verify Phase (2026-05-29)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`src/lib/beatDispatch.ts`, `src/hooks/useWebSocket.ts`, `src/App.tsx` — 67-8 diff only; test files excluded per filter)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication; `beatDispatchBlockReason` has no pre-existing equivalent; the 3-point `sessionBound` reset pattern is consistent with existing `useWebSocket` state-reset conventions. |
| simplify-quality | clean | Minimal public API, explicit return types, no `as any`, no dead code; gate precedence matches documented order; imports/wiring correct. |
| simplify-efficiency | clean | No over-engineering; the post-gate `if (!beat) return` is correctly read as justified type-narrowing / cheap defense-in-depth, not a smell. |

**Applied:** 0 high-confidence fixes (all clean). **Flagged for Review:** 0. **Noted:** 0. **Reverted:** 0.
**Overall:** simplify: clean

**Quality Checks:** `npx vitest run` → 171 files / **1663 tests, 0 failures**; `npx tsc --noEmit` → clean; ESLint clean on all changed files (2 pre-existing `App.tsx` warnings at :1334/:1904, untouched by 67-8).

### Spec-check Watch-items (from Architect)

1. **OTEL live acceptance** (`session_unbound`=0 + no `presence.multi_socket_attach` across a multi-beat confrontation) — **NOT exercised on the live stack in verify.** Rationale: (a) the strand is *churn-gated* — a clean-baseline multi-beat run shows `session_unbound`=0 *even on pre-fix code* (Dev's 2026-05-29 live repro already established this), so a happy-path OTEL run cannot distinguish fixed-from-unfixed; (b) forcing the churn (socket bounce) to truly exercise the fix was explicitly declined by the Operator during diagnosis. The static verify (RED→GREEN invariants + gate suites + tsc + 1663 tests) gives high confidence. **Recommendation:** validate this observable in the next live playtest (the venue where the bug surfaced) rather than a synthetic verify run. Carried as a non-blocking delivery finding. *(Not a quality-gate blocker.)*
2. **No false-block** — **PASS (code review).** `sessionBound` is set `true` on SESSION_EVENT `connected`/`ready`, which is the same event that transitions to game phase (`sessionPhase="game"`); confrontations (and therefore beats) only exist in game phase, so `sessionBound` is `true` whenever a beat can be selected. The only window it is `false` mid-game is a genuine reconnect's `AwaitingConnect` gap — blocking a commit there is the intended behavior, not a false-block, and it clears the instant `ready` re-arrives. 1663-test suite confirms no legitimate beat-dispatch path regressed.
3. **Multi-socket presence regression** — **PASS (code review).** `createSocket`'s close only targets `wsRef.current` (the prior socket *within this hook instance*) and only when OPEN/CONNECTING. A legitimate same-player multi-socket scenario is multiple tabs/devices → separate page contexts → separate `useWebSocket` instances, each with its own `wsRef`; instance A never closes instance B's socket. Server-side ref-counted presence (`session_room.disconnect` / `presence.disconnect_skipped`) is untouched. `connect()`'s no-op-when-OPEN likewise only affects re-entrant connect on the same instance. No regression.

**Handoff:** To Reviewer (The Merovingian) for code review. Layers 1+3 are GREEN and quality-clean; the one outstanding item is the live-OTEL acceptance, recommended for the next playtest (non-blocking, documented).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (1663 tests green, tsc pass, 0 net-new smells; 2 pre-existing lint warnings outside diff) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 (low) | confirmed 1, dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 (test-file; high-conf) | confirmed 3, dismissed 0, deferred 0 |

**All received:** Yes (3 enabled returned; 6 disabled via `workflow.reviewer_subagents`)
**Total findings:** 5 confirmed (all Low/Medium, non-blocking), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict: APPROVED** — no Critical/High findings. Five confirmed Low/Medium findings, all non-blocking; a quick cleanup amend is recommended before merge (Operator's call).

### Observations

- `[VERIFIED]` **Layer 1 orphan-close is correct and No-Silent-Fallbacks-clean** — `useWebSocket.ts:142-156`: `detachHandlers(prev)` runs *before* `prev.close()`, so the close cannot re-enter the reconnect path (onclose nulled); the close fires only when `prev.readyState` is OPEN/CONNECTING, so the reconnect-timer path (prev already CLOSED) never double-closes. Complies with No Silent Fallbacks (explicit close, not a fallback).
- `[VERIFIED]` **`connect()` no-op guard does not break legitimate reconnect** — `useWebSocket.ts:211`: early-returns only when `readyState === WebSocket.OPEN`. A genuine reconnect (socket CLOSED) still calls `createSocket`. Satisfies the AC2 edge "don't over-correct into never-reconnect"; proven by the AC6 reconnect test (`useWebSocket-67-8`).
- `[VERIFIED]` **`sessionBound` lifecycle is complete and correctly ordered** — set `true` only on `connected`/`ready` (App:665, server-authoritative, not WS-open); reset `false` on non-OPEN readyState (App:1870 effect, deps `[readyState]` correct) and on `session_unbound` (App:1151). `handleBeatSelect` deps include `sessionBound` (App:1477) — no stale closure. Confirmed by `[RULE]` #6.
- `[VERIFIED]` **Wiring intact** — `[RULE]` #16: `beatDispatchBlockReason` has a non-test consumer (App:1425); `useWebSocket` reaches production via `useGameSocket`→`AppInner`. Full suite 1663 green proves end-to-end.
- `[SEC][LOW]` **Unreachable silent-drop branch** at `App.tsx:1445` (`if (!beat) return;`). The gate (`beatDispatchBlockReason`) already returns `unknown_beat` when the beat is absent and guarantees `confrontationData` non-null, so `.find()` always succeeds and this branch is provably unreachable. But it matches the No-Silent-Fallbacks `<critical>` rule — **confirmed, not dismissed**. Recommend making it loud: `if (!beat) { console.error('[beat-dispatch] INVARIANT: beat absent post-gate', beatId); return; }`.
- `[RULE][LOW]` **`as any` in test** at `useWebSocket-67-8-duplicate-socket.test.ts:101` (`globalThis.WebSocket = MockWebSocket as any`). Matches the existing `useWebSocket-teardown.test.ts` convention, but rule #1/#8 flag `as any`. Recommend `as unknown as typeof WebSocket`. Confirmed, Low (test-only).
- `[RULE][LOW]` **Unguarded non-null assertions** at `useWebSocket-67-8-duplicate-socket.test.ts:153/183/209` (`MockWebSocket.instances[0]!` after `connect()` with no preceding length assertion; line 129 *is* guarded). Tests still fail on regression, but with a panic rather than a clean assertion message. Recommend a `toHaveLength`/`toBeGreaterThan(0)` guard before each. Confirmed, Low (test-only).
- `[MEDIUM]` **`handleDiceThrow` does not re-check `sessionBound`** (App:1478+). The gate is on `handleBeatSelect` (roll *start*); if the session unbinds during the ~1-2s dice-physics animation, `handleDiceThrow` still flushes the `DICE_THROW` into the now-unbound socket. Within AC3's explicit allowance ("a true race must still reject — the assertion is 'no loop,' not 'never reject'") and the reactive `session_unbound` auto-rebind catches it (single reject + recovery, no loop). **Non-blocking**; recommend gating `handleDiceThrow` on `sessionBound` as belt-and-suspenders (fold into the Layer 2 follow-up).

### Rule Compliance (TypeScript lang-review + CLAUDE.md doctrine)

| Rule | Verdict | Evidence |
|------|---------|----------|
| #1 Type-safety escapes | 2 violations (test-only, Low) | `as any` test:101; unguarded `!` test:153/183/209. Production code (beatDispatch.ts, useWebSocket.ts, App.tsx hunks) clean — no new casts/`!`/ts-ignore. |
| #4 Null/undefined (`??` vs `||`) | Pass | `?? '?'` (beatDispatch:58), `?.` + `if (!beat) return` (App:1442/1445), `wsRef.current?.readyState` (useWebSocket:211). |
| #6 React/JSX hooks | Pass | New effect deps `[readyState]` complete; `handleBeatSelect` deps include `sessionBound`; setState setters correctly omitted. |
| #8 Test quality | 1 violation (Low) | `as any` test:101 (same as #1). Otherwise meaningful assertions, real-interface mocks, wiring test present. |
| #11 Error handling | Pass | No new catch blocks; `session_unbound` is string-equality, not exception path. |
| #13 Fix-introduced regressions | Pass | createSocket close guarded to OPEN/CONNECTING (no double-close); safe `false` default for `sessionBound`. |
| No Silent Fallbacks (`<critical>`) | 1 latent violation (Low) | `if (!beat) return` (App:1445) — unreachable but should be loud (see observation). All blocked beats otherwise warn/notify. |
| No Stubbing (`<critical>`) | Pass | All code fully implemented; no shells. |
| Verify Wiring (`<critical>`) | Pass | `beatDispatchBlockReason` consumed in production (App:1425); wiring test asserts it. |
| Every suite needs a wiring test (`<critical>`) | Pass | `beat-commit-session-bound-wiring-67-8.test.tsx` covers the App integration. |

### Devil's Advocate

Argue the code is broken. **First attack — the false-block deadlock.** `sessionBound` starts `false` and only flips `true` on a server `connected`/`ready`. If the server completes its WS handshake but never emits `connected`/`ready` (a server bug, a dropped event, a partial bind), `sessionBound` stays `false` forever and *every* beat-commit is refused with "Server reconnecting — please retry," with no escape. The player is soft-locked mid-confrontation. Is this worse than the original bug? No — in that scenario the session genuinely isn't bound, so commits would be rejected anyway; the gate converts a rejection *loop* into a single honest "can't act yet" message, which is strictly better and No-Silent-Fallbacks-correct. But it does make the UI's liveness depend entirely on the server's `ready` emission — a coupling worth noting. **Second attack — the mid-physics race.** As flagged (Medium), `handleDiceThrow` ignores `sessionBound`; a remount during the dice animation still flushes a `DICE_THROW` into an unbound socket. The spec explicitly tolerates a single such reject (no loop), and reactive recovery handles it — but it means AC3's "first-attempt roll" can still cost one bounce in this narrow window. **Third attack — `connect()` no-op hides a stale socket.** If a caller ever needs to force-reconnect to a *different* endpoint while OPEN, `connect()` silently no-ops and they keep talking to the old socket. No such caller exists today (url is static; session switches remount the hook), but the contract is now "you cannot force-replace a live socket via connect()" — `createSocket` is the only path that replaces a live socket. **Fourth — test brittleness.** The wiring tests are source-grep regexes; a benign refactor (renaming `block`, reordering the gate object) breaks them with no behavioral change. They guard wiring but will generate false failures. **Conclusion:** none of these rise to blocking — the worst (false-block deadlock) is strictly better than the status quo and reflects true server state; the mid-physics race is spec-sanctioned. All are documented as findings/recommendations.

### Decision

**APPROVED.** No Critical/High. The five confirmed findings are Low/Medium and non-blocking. Recommended (non-blocking) cleanup before merge: (1) make `App.tsx:1445` loud; (2) `as unknown as typeof WebSocket` at test:101; (3) length-guard the `!` assertions at test:153/183/209; (4) gate `handleDiceThrow` on `sessionBound`. Items (1)-(3) are trivial; (4) pairs naturally with the Layer 2 follow-up. Proceed to spec-reconcile.

## Architect Assessment (spec-check — 2nd pass, post-cleanup amend)

**Spec Alignment:** Improved; no new drift. The post-review cleanup (`4d516b4`) resolved all 5 Reviewer findings.
**Mismatches Found:** Still 1 (the AC2 "no re-run of handshake" / Layer-2 deferral — unchanged, Option D, Operator-sanctioned).

- **AC3 alignment strengthened:** `handleDiceThrow` now re-checks `sessionBound` at send-time and refuses (resets dice state) if the session unbound during dice physics — closing the mid-physics race I flagged as a Medium in the 1st-pass review. AC3 "first-attempt roll" is now robust across the full roll lifecycle (start *and* send), not just roll-start.
- **No-Silent-Fallbacks:** the previously-unreachable `App.tsx:1445` branch is now loud (`console.error` invariant). Compliant.
- **Test hygiene:** `as any`→typed cast and length-guarded `!` assertions; new wiring test pins the `handleDiceThrow` gate. No spec impact.
- **No new spec deviations introduced** by the amend. Structural spec-check gate PASS. Full suite 1664/1664 green, tsc + eslint clean.

**Decision:** **Proceed to verify.** Alignment is equal-or-better than the 1st pass; the lone Major deferral is unchanged and remains an Operator-sanctioned Option-D.

## TEA Assessment — Verify Phase (2nd pass, post-cleanup amend, 2026-05-29)

**Phase:** finish
**Status:** GREEN confirmed

**Scope:** The cleanup amend (`4d516b4`) changed exactly one code file — `src/App.tsx` (+21/-2: the `handleDiceThrow` `sessionBound` gate and the loud invariant branch) — plus two test files (excluded from simplify). `beatDispatch.ts` and `useWebSocket.ts` are unchanged since the 1st-pass verify (which was simplify-clean across all three).

### Simplify Report

**Decision: focused verify — full simplify fan-out NOT re-run (justified).** The only code delta is a 21-line, review-*mandated* cleanup produced in direct response to the Merovingian's adversarial findings and re-confirmed by Neo's 2nd-pass spec-check. The 1st-pass simplify trio returned clean on the larger diff; re-fanning three subagents over a 21-line vetted delta is disproportionate. Direct review of the delta: the `handleDiceThrow` guard mirrors the established `handleBeatSelect` gate pattern (no new abstraction, no duplication — both refuse-and-reset, neither buffers); the loud `console.error` invariant replaces a silent return (a quality *improvement*). No findings.
**Overall:** simplify: clean (focused).

**Quality Checks:** `npx vitest run` → 171 files / **1664 tests, 0 failures**; `npx tsc --noEmit` clean; ESLint clean on all touched files (2 pre-existing `App.tsx` warnings at :1334/:1929, not introduced here).

**Watch-items (carried, unchanged):** the live-OTEL acceptance remains recommended for the next playtest (non-blocking finding); watch-items 2 (no false-block) and 3 (multi-socket presence) confirmed PASS in the 1st pass and unaffected by the cleanup.

**Handoff:** To Reviewer (The Merovingian) for re-review — confirm the 5 findings are resolved.

## Subagent Results — 2nd Pass (re-review of cleanup amend `4d516b4`)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (1664 tests green, tsc clean, eslint 0 errors, 0 net-new smells) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none (both fixes verified; no new issue) | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | none (3 prior findings resolved; 0 new violations) | N/A |

**All received:** Yes (3 enabled returned, all clean; 6 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 new; all 5 from the 1st pass confirmed resolved.

## Reviewer Assessment — 2nd Pass (re-review of cleanup amend)

**Verdict: APPROVED.** All five 1st-pass findings resolved; no new findings; no Critical/High.

### Findings resolution (1st-pass → verified in `4d516b4`)

- `[MEDIUM]` **handleDiceThrow `sessionBound` gate** → ✅ RESOLVED. `handleDiceThrow` now early-returns on `!sessionBound`, clearing `pendingBeatIdRef`/`pendingPlayerActionRef`/`diceResult`/`diceRequest` *before* `send()` (security agent confirmed: refuse-and-discard, no buffering, no leakage); `sessionBound` added to the deps `[diceRequest, sessionBound, send]` (rule-checker #6). The AC3 mid-physics race is closed; the roll lifecycle is gated at both start and send.
- `[SEC][LOW]` **`App.tsx` silent `if (!beat)` branch** → ✅ RESOLVED. Now `console.error`s the invariant violation (No Silent Fallbacks); log-only, no player-surface leakage.
- `[RULE][LOW]` **`as any` in test** → ✅ RESOLVED. Now `as unknown as typeof WebSocket` — confirmed the correct idiom for a `globalThis` browser-API override, not a new escape.
- `[RULE][LOW]` **unguarded `instances[0]!` (×3)** → ✅ RESOLVED. Each now preceded by `expect(MockWebSocket.instances).toHaveLength(1)`.
- New wiring test pins the `handleDiceThrow` gate (suite 1664 green, +1).

### Observations

- `[VERIFIED]` handleDiceThrow refuse path is No-Silent-Fallbacks-clean and non-buffering — guard precedes `send()`; all dice state reset; `[SEC]` confirmed no queue/flush path.
- `[VERIFIED]` Loud invariant — `console.error` replaces the silent return; `[SEC]` confirmed log-only.
- `[VERIFIED]` Hook deps correct — `handleDiceThrow` deps `[diceRequest, sessionBound, send]`; no stale closure (`[RULE]` #6).
- `[VERIFIED]` Test hygiene — `as unknown as typeof WebSocket` + three `toHaveLength(1)` guards (`[RULE]` #1/#8).
- `[VERIFIED]` No regressions — full suite 1664/1664, tsc clean, eslint 0 errors (`[preflight]`).

### Devil's Advocate (delta-focused)

Could the new `handleDiceThrow` guard break a *legitimate* roll? It refuses only when `!sessionBound`. During normal bound play `sessionBound` is `true` (set on `connected`/`ready`, held until a drop/unbind), so a legitimate roll passes — the guard fires only in the exact window the original bug occupied. Could resetting `diceRequest`/`diceResult` on refusal strand the dice overlay? No — clearing them returns the overlay to beat-selection, the transient notice tells the player to retry, and the reactive `session_unbound` rebind restores the session shortly. Could the refusal lose intent silently? No — it is loud (console.warn + player-facing transient error) and the discarded roll is re-rollable. The only residual is the pre-existing coupling (UI liveness depends on the server's `connected`/`ready` emission) noted in pass 1 — unchanged by this delta. Nothing new is broken.

### Decision

**APPROVED — proceed to spec-reconcile.** The complete fix (Layers 1+3, all 5 review findings resolved) is clean. The carried items remain the live-OTEL playtest validation (non-blocking) and the Layer-2 connection-hoist follow-up (documented).