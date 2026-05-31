---
parent: context-epic-59.md
workflow: trivial
---

# Story 59-21: Decide unseated-spectator CONFRONTATION policy — empty-beats card vs no frame

## Business Context

Story 59-16 collapsed CONFRONTATION delivery to a single class-filtered
per-recipient path. As part of that collapse, the supplier made a deliberate
choice: a connected-but-unseated socket (lobby spectator, no PC at the table)
resolves to `(None, None)` and receives **nothing** — the supplier returns
`None`, and `emit_event` skips that recipient silently. The rationale was that
in real multiplayer every player seats a PC, so an unseated socket is a
spectator with no legal moves; an empty-beats CONFRONTATION card would be
visual noise (a combat tab they can't act on).

This is a **policy decision story**, not a feature build. It exists because the
2026-04-26 S2 doctrine ("peers are notified when a confrontation starts") and
SOUL.md's **"The Guitar Solo"** pull in the opposite direction: when one player
is soloing a negotiation/dogfight/duel, *"the rest of the table must never
become a silent audience watching a screen they can't touch."* The open
question is whether a connected non-combatant observer should at least *see*
that a fight is happening — an active-but-empty-beats card that says "a
confrontation is underway" without offering moves — rather than getting nothing
at all.

The design tension is genuine: SOUL says don't make spectators a silent
audience; the 59-16 rationale says an actionless card *is* the noise that makes
spectating feel worse, not better. The right answer depends on whether
"unseated/lobby socket" in real play ever means "a player at the table who
simply hasn't seated a PC yet" (in which case the empty card preserves the
notify intent) versus "a genuine lobby observer who is not a player" (in which
case silence is correct). Keith/Architect own this call; this story records the
decision and, if the decision is "yes", implements the minimal supplier change
plus a test.

## Technical Guardrails

The surface is the per-recipient confrontation frame supplier. Real anchors:

- **`sidequest/server/dispatch/confrontation.py:384`** —
  `make_confrontation_frame_supplier(...)`. The returned `_frame_for(player_id)`
  (line 416) calls `resolve_recipient_pc(...)`. Its three documented outcomes
  (docstring lines 400-409):
  - seated PC resolves → class-filtered `ConfrontationPayload`;
  - `(None, None)` unseated/lobby socket → **return `None` silently** (the
    behavior this story re-examines);
  - `(None, actor)` seated PC whose class won't resolve → fire the
    `confrontation_recipient_unresolved` ERROR span, then return `None` (never
    the union). **This third arm is firm and out of scope — do not touch it.**
- **`sidequest/server/websocket_session_handler.py:1654`** — the call site that
  builds `_confrontation_frame_for` and passes it as `per_recipient_payload` to
  `self._emit_event("CONFRONTATION", ...)` (line 1669-1673). The "unseated/lobby
  socket gets nothing silently" contract is documented inline at lines 1641-1645.
- **`build_clear_confrontation_payload(...)`** at
  `sidequest/server/dispatch/confrontation.py:324` — the existing empty-beats
  shape (`beats: []`, all-empty metrics, `genre_slug`, plus a flag). Note it
  currently sets **`active: False`** (overlay-unmount semantics, App.tsx:435 keys
  the dispatch branch on `active !== false`). The "decide-yes" path needs an
  empty-beats payload with **`active: True`** so the spectator's overlay *mounts*
  and shows "a fight is happening" rather than unmounting. Do NOT reuse
  `build_clear_confrontation_payload` verbatim — its `active: False` would unmount
  the card. A decide-yes implementation builds an active-empty-beats variant.

**Firm invariant (unaffected either way):** the canonical full-union payload is
persisted to the EventLog only and is **never** sent to a client socket. Neither
decision outcome may deliver the union to any recipient. The (None, actor)
fail-loud ERROR-span arm is untouched.

**Reuse-first:** if the decision is "yes", reuse the existing
`build_clear_confrontation_payload` field shape as the template for an
active-empty-beats builder (same dict keys, flip `active` to `True`, beats stay
`[]`) — do not invent a new payload schema. `ConfrontationPayload` (from
`sidequest.protocol.messages`) is the existing typed wrapper.

## Scope Boundaries

**In scope:**
- A recorded decision (Architect/Keith) on whether unseated/lobby spectators
  receive an active empty-beats CONFRONTATION card or continue to receive
  nothing.
- **If decide-yes:** the `_frame_for` supplier returns an active-empty-beats
  payload (`active=True`, `beats=[]`) for the `(None, None)` case instead of
  `None`; plus a test asserting that shape reaches an unseated recipient.
- **If decide-no:** document the decision (rationale: noise vs. notify) in this
  context doc's resolution and the story session, and close. No code change.

**Out of scope:**
- The `(None, actor)` seated-PC-class-unresolved fail-loud arm — firm, untouched.
- The union-never-to-a-socket invariant — unaffected by either outcome.
- Any change to seated-PC class filtering or beat projection.
- Multi-seat / sealed-visibility (PvP) modes — not implemented, not in play.
- The clear/unmount branch (`prior_live and not now_live`) — separate path.

## AC Context

Because this is a decision story, the ACs split by outcome. Exactly one branch
applies once the decision is made.

**AC (decision):** A decision is recorded — "spectators receive an active
empty-beats card" (yes) or "spectators receive nothing" (no) — with the
SOUL "Guitar Solo" vs 59-16-noise rationale captured in the story session.

**Decide-YES branch:**
- **AC-Y1 — supplier returns the card:** For a `(None, None)` recipient,
  `make_confrontation_frame_supplier(...)`'s `_frame_for(player_id)` returns a
  `ConfrontationPayload` with `active=True` and `beats=[]` (not `None`).
  *Test:* build a supplier over a snapshot where `resolve_recipient_pc` yields
  `(None, None)` for a given `player_id`; assert the returned payload is
  non-`None`, `active is True`, `beats == []`.
- **AC-Y2 — no false mount for the clear case:** The new active-empty-beats
  builder is distinct from `build_clear_confrontation_payload` (which keeps
  `active=False`). *Test:* assert the unmount/clear payload still serializes
  `active=False`; the spectator-notify payload serializes `active=True`.
- **AC-Y3 — invariant preserved:** The union payload is still never returned by
  the supplier for any recipient. *Test:* assert the spectator card's `beats`
  is empty (not the full union beat list) and no canonical-union fields leak.
- **Edge case:** a genuinely seated PC still gets the full class-filtered card;
  the empty-beats path fires **only** for `(None, None)`. *Test:* a seated PC and
  an unseated socket against the same supplier get different payloads (filtered
  vs empty-beats-active).

**Decide-NO branch:**
- **AC-N1 — behavior documented:** This context doc's resolution and the story
  session record that current behavior (supplier returns `None` for
  `(None, None)`, `emit_event` skips) is the intended policy, with rationale.
- **AC-N2 — no code change:** `make_confrontation_frame_supplier` and the wssh
  call site are unchanged; existing 59-16/59-20 tests remain green.

## Assumptions

- "Unseated/lobby socket" maps cleanly to `resolve_recipient_pc → (None, None)`;
  there is no fourth recipient category. (If a fourth shape exists, log a Design
  Deviation — the decision's scope shifts.)
- The UI's `ConfrontationPayload` consumer (App.tsx, `active !== false` branch)
  will mount an overlay on an `active=True`/`beats=[]` payload and render it as
  an informational "fight in progress" card without crashing on empty beats. If
  the decision is "yes", this UI behavior must be confirmed before close — a
  card the client can't render is worse than silence. (UI is read-only for this
  server-repo story; flag as a Delivery Finding if the client needs a change.)
- The 2026-04-26 S2 "peers are notified" doctrine refers to non-combatant
  *observers*, not to peers who are themselves seated (those already get their
  own filtered card). The decision concerns only the spectator class.
- Workflow is `trivial` — a decision plus (at most) a single-arm supplier tweak
  and one test, not a TDD red/green cycle across multiple files.
