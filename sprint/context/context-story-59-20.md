---
parent: context-epic-59.md
workflow: tdd
---

# Story 59-20: Route dice mid-turn + connect resume through the single emit_event(per_recipient_payload) supplier; delete room_broadcast(union)

## Business Context

This is a perception-firewall correctness fix (ADR-104/105). SideQuest delivers asymmetric, per-recipient information during multiplayer confrontations — the table's trust depends on hidden state staying hidden. Story 59-16 established `emit_event(per_recipient_payload=...)` as the single authoritative filtered-delivery seam and converted the post-narration CONFRONTATION START path and the reconnect path to it (union → EventLog only; one class-filtered frame per socket including the emitter; fail-loud `confrontation.recipient_unresolved` span on a seated-but-unresolvable recipient; `None → skip` for unseated spectators).

The dice mid-turn / flee path was explicitly **deferred** from 59-16 (left AC2/AC3/AC5 partial). It still runs the legacy `room_broadcast(union)` plus a separate per-recipient overlay (the Story 49-7 mechanism). In production the overlay wins last-message-wins, so the common-case flee is correct — but the union still hits sockets, leaving a **residual leak on a reconnect that races the mid-turn emit**. This story closes that leak by routing the dice mid-turn path through the same supplier and deleting the union + overlay. No player-facing surface changes; pure delivery-correctness.

## Technical Guardrails

**Key files to modify:**
- `sidequest/server/dispatch/dice.py:647-692` — mid-turn delivery (CURRENT: `room_broadcast(union)` + per-recipient overlay loop). Route through `emit_event(per_recipient_payload=...)`; delete union + overlay.
- `sidequest/handlers/dice_throw.py` — caller of the dice.py delivery path; reconcile with the supplier change.
- `sidequest/handlers/connect.py:1515-1568` — resume path. Already single-filtered; dedupe to share the same supplier helper introduced/used by 59-16.
- `sidequest/server/emitters.py:391-397, 625-632` — emitter-absent / legacy-no-EventLog fallbacks currently return the canonical union as `out_to_self` when the emitter can't be identified. Return an empty/clear frame instead. (LOW)
- `tests/server/test_dice_throw_confrontation_emit.py` — momentum-sync test on a `_StubRoom`; reconcile (seat + inject a class on the stub, OR convert to the real-room harness).

**Patterns to follow:**
- The 59-16 single-supplier seam (`emit_event(per_recipient_payload=...)`) is the canonical mechanism — reuse it, do not reintroduce a parallel path.
- Fail-loud doctrine (No Silent Fallbacks): seated-but-unresolvable recipient must raise the `confrontation.recipient_unresolved` span; unseated → None→skip.
- Don't reinvent — connect.py resume is already correct; share the helper, don't fork it.

**Reference docs:**
- ADR-104 (Perception Filtering at the Tool Layer), ADR-105 (Broadcast-Layer Perception Firewall), ADR-116 (A Confrontation Requires an Other).
- Story 59-16 session: `sprint/archive/59-16-session.md`.
- Spec: `docs/superpowers/specs/2026-05-26-confrontation-single-filtered-delivery.md` §Implementation step 3.

## Scope Boundaries

**In scope:**
- Route dice mid-turn delivery through `emit_event(per_recipient_payload=...)` and DELETE `room_broadcast(union)` + the overlay loop (`dice.py` + `dice_throw.py`).
- Reconcile/migrate `tests/server/test_dice_throw_confrontation_emit.py` so it exercises a seated confrontation (real delivery), not a no-op stub.
- Dedupe `connect.py` resume against the shared supplier helper.
- LOW: `emitters.emit_event` emitter-absent / legacy-no-EventLog fallbacks return an empty/clear frame instead of the union as `out_to_self`.
- OPTIONAL LOW: wrap `confrontation_recipient_unresolved_span` in try/except for defense-in-depth.

**Out of scope:**
- The post-narration START path and reconnect filtering already converted by 59-16.
- The cross_player redaction gap (Story 59-9) — adjacent firewall surface, separate story.
- Any change to confrontation seating/membership semantics (ADR-116 / 59-13/59-17 territory).

## AC Context

**AC1 — Dice mid-turn routes through the single supplier; union deleted.**
- After the change, `dispatch/dice.py` mid-turn delivery calls `emit_event(per_recipient_payload=...)` and there is NO `room_broadcast(union)` call and NO separate per-recipient overlay loop in the mid-turn path (dice.py + dice_throw.py).
- Test: drive a seated multi-player confrontation through the dice mid-turn / flee path; assert each socket receives exactly one class-filtered frame (the recipient's payload), and that no socket receives the union frame. A reconnect racing the emit must not see union content.
- Edge: the emitter's own socket receives its own filtered frame (incl. emitter), per 59-16.

**AC2 — Fail-loud on seated-but-unresolvable; skip on unseated.**
- A seated recipient whose payload cannot be resolved raises/emits the `confrontation.recipient_unresolved` span (fail-loud, not silent union fallback).
- An unseated spectator → `None → skip` (no frame), not a union frame.
- Test: pin both — assert the span fires for the seated-unresolvable case; assert unseated gets no delivery.

**AC3 — connect.py resume shares the supplier helper.**
- The resume path (connect.py:1515-1568) and the dice mid-turn path call the same helper; no duplicated filtering logic.
- Test: a reconnect during an active confrontation receives the same single-filtered frame the live path would produce.

**AC4 (LOW) — emitter-absent fallback returns empty frame, not union.**
- `emitters.emit_event` fallbacks (391-397, 625-632) return an empty/clear `out_to_self` when the emitter can't be identified.
- Test: invoke the fallback path (emitter absent / no EventLog) and assert the returned `out_to_self` is empty/clear, not the canonical union.

## Assumptions

- The 59-16 `emit_event(per_recipient_payload=...)` supplier and its shared helper exist on `develop` and are importable from the dice mid-turn path. (Branch is stacked on 59-16, merged.)
- `space_opera` (SWN, opposed_check combat) is the realistic pack for an e2e seated-confrontation fixture; the "wire BOTH resolution paths" trap means a `dispatch_dice_throw` simple-DC test alone will NOT exercise the opposed_check path that real combat uses. Tests must cover the real seated/opposed path.
- The `_StubRoom` in the existing test does not seat a confrontation or inject a class, so as written it no-ops the production filtering. Reconciling it requires either seating + class injection or moving to the real-room harness.
- Full-suite gating requires `SIDEQUEST_DATABASE_URL` (post-ADR-115) and `SIDEQUEST_GENRE_PACKS` set; a scoped `tests/server/dispatch/` subset will miss bystander-leak regressions one directory up (cf. 59-17).

## Interaction Patterns

Not applicable — backend delivery-path change, no UI flow.

## Accessibility Requirements

Not applicable — no frontend surface.

## Visual Constraints

Not applicable — no UI.
