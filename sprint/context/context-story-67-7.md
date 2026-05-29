---
parent: context-epic-67.md
workflow: tdd
---

# Story 67-7: Duplicate-socket reconnect loop strands session in AwaitingConnect — dice/action frames hard-rejected mid-confrontation

## Business Context

Epic 67 is about turn/socket robustness — a transport failure must not make the
game feel broken even when the engine is fine. Playtest 2026-05-28 (coyote_star
solo) hit exactly that: committing a dogfight beat fired `DICE_THROW` frames the
server rejected with `session.message_rejected_unbound type=DICE_THROW
state=AwaitingConnect` (×4+); a single beat took ~5 rejected attempts plus a full
page reload before one roll landed (finding #C5). The dogfight *felt* broken
even though the beat math works — the player can't reliably roll. This story
removes the transport-layer block so confrontations are playable without the
reload dance.

## Technical Guardrails

**Provenance — symptom captured, root cause NOT yet pinned (needs live repro).**
Traced as far as static logs allow during the 2026-05-28 FIXER pass; the
remaining diagnosis requires reproducing the remount loop live.

### What the logs show

- Repeated `INFO [sidequest.handlers.dice_throw] session.message_rejected_unbound
  type=DICE_THROW state=AwaitingConnect` on each beat commit; one `ORBITAL_INTENT`
  rejected the same way.
- **Duplicate sockets:** "connection open" ×2, two `ws.connection_accepted` /
  `chargen_gate` cycles per reconnect — the page appears to remount repeatedly.
- The `AwaitingConnect`→`Playing` handshake does not complete before the dice
  frame is sent, so the frame is rejected.
- After a deliberate page reload the handshake completed (`slug_resumed turn=3`,
  `slug_resume_confrontation_emitted ship_combat`) and the very next Broadside
  resolved (`dice.throw_resolved total=22 CritSuccess`). **The engine is fine; the
  transport/session-binding is the block.**

### The rejection itself is CORRECT — do not weaken the guard blindly

- Every handler guards on Playing state: `sidequest/handlers/dice_throw.py:57`,
  `check_throw.py:101`, `player_action.py:264`, `orbital_intent.py:41`,
  `yield_action.py:71`, `journal_request.py:112`. You genuinely cannot resolve a
  dice throw before the session FSM binds. The bug is the **churn that keeps the
  session unbound**, not the guard.

### Two angles (the story must pick a primary)

1. **Root cause (preferred):** eliminate the duplicate-socket / repeated
   `ws.connection_accepted` reconnect cycle. Determine whether it is a UI
   reconnect/remount loop (`sidequest-ui` mount logic / `useWebSocket` /
   `useGameSocket`) or a server session-binding race. The `window.WebSocket` patch
   being wiped mid-session is a UI-side clue.
2. **Hardening (secondary):** buffer/retry a beat's action frame across a
   reconnect until `Playing`, rather than hard-rejecting. This is a **cross-handler
   behavior change** — it touches the same "heavy-hammer WS teardown" class that
   was explicitly scoped OUT of #G3, so it needs a deliberate decision here, not a
   one-off patch in `dice_throw.py`.

### Constraints

- **No Silent Fallbacks:** if a frame is genuinely unbound, the rejection stays
  loud; any buffering must be explicit and bounded (no silent swallow / infinite
  retry).
- Distinguish "rejected because genuinely unbound" from "churn from a spurious
  reconnect" in telemetry so the GM panel can tell a real guard from transport
  noise.
- Adjacent surface: **59-20** (per-recipient delivery firewall — distinct seam,
  not this bug), #G3/#G1 (WS teardown hardening).

## Scope Boundaries

**In scope:**
- Identify and fix the duplicate-socket / spurious-reconnect cause (UI remount
  loop or server bind race).
- A recorded DECISION on whether pre-handshake action frames are
  buffered/retried-until-Playing vs left hard-rejected, applied consistently if
  chosen.
- Telemetry distinguishing genuine-unbound rejection from reconnect churn.
- Regression coverage for the reconnect/bind path.

**Out of scope:**
- The dice/beat resolution engine (works once bound; not touched).
- The per-recipient delivery firewall (59-20).
- A general WS-teardown-semantics overhaul beyond what #C5 requires (#G3 territory).
- Confrontation instantiation correctness (that's 59-23).

## AC Context

1. **Root cause identified:** the duplicate-socket / repeated
   `ws.connection_accepted` cycle is explained (UI remount vs server bind race)
   with log/OTEL evidence captured in the story. *This likely requires a live
   repro of the dogfight churn.*
2. **No spurious second socket:** a solo confrontation session no longer opens a
   second socket / re-runs the connect handshake; `AwaitingConnect`→`Playing`
   completes before action frames are submitted.
3. **First-attempt roll:** committing a dogfight beat lands its `DICE_THROW` on
   the first attempt — no `message_rejected_unbound` loop, no required page reload.
   *Verify:* drive a beat commit against a freshly-connected session → one roll
   resolves.
4. **Decision recorded:** eliminate-the-loop (preferred) and/or
   buffer-until-Playing; if the latter, applied across affected handlers uniformly,
   never one-off.
5. **Telemetry:** a span/log distinguishes genuine-unbound rejection from
   reconnect churn.
6. **Regression coverage** for the reconnect/bind path; if reproducible in MP as
   well as solo, the fix covers both.

## Assumptions

- The churn is reproducible (it was consistent in the 2026-05-28 session) — a live
  repro session in oq-2 with logs is the practical path to pinning it.
- Observed solo so far; unknown whether MP exhibits the same loop. The fix should
  not assume solo-only without checking.
- The fix is primarily transport/UI; the engine and per-turn logic are sound and
  out of scope.
