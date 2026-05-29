---
story_id: "59-20"
jira_key: null
epic: "59"
workflow: "tdd"
---
# Story 59-20: Route dice mid-turn + connect resume through the single emit_event(per_recipient_payload) supplier; delete room_broadcast(union)

## Story Details
- **ID:** 59-20
- **Jira Key:** (none - personal project)
- **Workflow:** tdd
- **Stack Parent:** 59-16 (merged to develop; feat/confrontation-single-filtered-delivery)
- **Branch:** feat/59-20-route-dice-midturn-single-supplier
- **Repos:** sidequest-server

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-29T10:12:42Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-29T00:00:00Z | 2026-05-29T09:22:07Z | 9h 22m |
| red | 2026-05-29T09:22:07Z | 2026-05-29T09:45:05Z | 22m 58s |
| green | 2026-05-29T09:45:05Z | 2026-05-29T10:00:48Z | 15m 43s |
| spec-check | 2026-05-29T10:00:48Z | 2026-05-29T10:01:55Z | 1m 7s |
| verify | 2026-05-29T10:01:55Z | 2026-05-29T10:06:10Z | 4m 15s |
| review | 2026-05-29T10:06:10Z | 2026-05-29T10:11:28Z | 5m 18s |
| spec-reconcile | 2026-05-29T10:11:28Z | 2026-05-29T10:12:42Z | 1m 14s |
| finish | 2026-05-29T10:12:42Z | - | - |

## Story Summary

Follow-up to story 59-16 (single filtered CONFRONTATION delivery). 59-16 converted the post-narration START path and reconnect to the single emit_event(per_recipient_payload=...) supplier. This story addresses the deferred dice mid-turn/flee path that still uses room_broadcast(union) + a separate per-recipient overlay, creating a residual delivery leak on reconnects.

### Scope
1. Route dice mid-turn through the same emit_event supplier and DELETE room_broadcast(union) + the overlay loop
2. Deduplicate handlers/connect.py resume path against the same supplier
3. Clean up emitter-absent fallbacks to return empty frames instead of union
4. Reconcile/migrate affected tests

### Key Files
- `sidequest/server/dispatch/dice.py:647-692` — mid-turn delivery (CURRENT: room_broadcast + overlay)
- `sidequest/handlers/dice_throw.py` — caller of dice.py delivery
- `sidequest/server/emitters.py` — emit_event supplier and fallback paths
- `sidequest/handlers/connect.py:1515-1568` — resume path (to be shared)
- `tests/server/test_dice_throw_confrontation_emit.py` — tests needing reconciliation

### Design Context
- ADR-105: Perception Filtering at the Tool Layer / Broadcast-Layer Perception Firewall
- ADR-116: A Confrontation Requires an Other — Participant Membership Invariant
- Story 59-16 session: `sprint/archive/59-16-session.md`
- Spec: `docs/superpowers/specs/2026-05-26-confrontation-single-filtered-delivery.md` §Implementation step 3

## Sm Assessment

**Routing decision:** Hand off to TEA (Fezzik) for the RED phase. This is a TDD/phased workflow on a single repo (sidequest-server).

**What this story is:** A delivery-path consolidation, not a new feature. 59-16 already proved the `emit_event(per_recipient_payload=...)` supplier as the single filtered-delivery seam for the post-narration START + reconnect paths. The dice mid-turn/flee path was explicitly DEFERRED from 59-16 (left AC2/AC3/AC5 partial) and still runs the legacy `room_broadcast(union)` + per-recipient overlay (Story 49-7 mechanism). In production the overlay wins last-message-wins so flee is common-case-correct — the bug is a residual union leak to sockets on a reconnect racing the mid-turn emit.

**Why it matters to the playgroup:** This is a perception-firewall correctness fix (ADR-104/105). It serves the table's trust that hidden state stays hidden during MP confrontations — the kind of leak that's invisible until someone reconnects mid-fight. Pure correctness; no player-facing surface change.

**Scope is well-bounded** (≈4 edits, see Key Files): (1) route dice mid-turn through emit_event + delete the union/overlay in dice.py + dice_throw.py; (2) dedupe connect.py resume against the shared supplier; (3) LOW: emitter-absent fallbacks return empty frame not union; (4) optional LOW try/except wrap. The thorny part is the test reconcile: `tests/server/test_dice_throw_confrontation_emit.py` is a momentum-sync test on a `_StubRoom` — TEA must decide seat+inject-class on the stub OR convert to the real-room harness.

**TEA watch-items:**
- The RED test must exercise the real opposed/seated confrontation delivery path, not a synthetic stub that no-ops in production (per the "wire BOTH resolution paths" trap — dispatch_dice_throw simple-DC AND narration_apply opposed_check).
- Fail-loud expectation: seated-but-unresolvable recipient must raise the `confrontation.recipient_unresolved` span; unseated → None→skip. Pin both.
- Gate on the FULL suite with `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS` set, not a scoped `tests/server/dispatch/` subset — the 59-17 bystander-leak regression hid one dir up.

**Context note:** No `sprint/context/` file was generated for 59-20; the story summary + key files + design context above are sufficiently detailed for TEA to begin, and the full upstream context lives in `sprint/archive/59-16-session.md` and the cited spec §Implementation step 3. Epic-59 context likewise inlined here.

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes
**Reason:** Delivery-behavior change with a perception-firewall correctness invariant — exactly the surface that needs behavioral pinning.

**Test Files:**
- `tests/server/test_dice_midturn_single_delivery.py` (NEW) — real-room harness driving the production DICE path (`handle_message(DiceThrowMessage)` → `dispatch_dice_throw` → mid-turn CONFRONTATION emit → inline narrator). Reuses the proven 59-16 helpers (`_inject_combat_pack`, `_seat`, `_install_live_combat_encounter`, `_wire_production_emit`, `_drain_confrontations`, `_beat_ids`, `_OTHER_CLASS_BEATS`) from `test_confrontation_single_delivery.py` so "class-filtered" has one source of truth.
- `tests/server/test_dice_throw_confrontation_emit.py` (DELETED) — its stub-room momentum tests asserted the `room_broadcast(union)` mechanism this story deletes, and its AC5 peer was UNSEATED (only the union broadcast reached it; post-fix it would get nothing). All contracts migrated to the seated real-room harness above.

**Tests Written:** 7 tests covering AC1, AC2, AC4 + two green invariant guards.
**Status:** RED — 5 failing (ready for Dev), 2 green guards (see deviations).

RED failures (verified locally with `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_TEST_DATABASE_URL` set to `postgresql://$USER@localhost:5432/sidequest_test`):
- `test_dice_midturn_delivers_one_filtered_frame_per_socket_no_overlay` — got 2 frames (union broadcast + overlay); also pins live post-apply momentum (45-3 contract migrated).
- `test_dice_midturn_no_union_reaches_any_socket` — union leaks cross-class beats to every socket.
- `test_dice_midturn_seated_unresolvable_fails_loud_no_union` — Ghost (seated, class undefined) receives the union; no `recipient_unresolved` span.
- `test_dice_midturn_unseated_socket_gets_nothing_silently` — lobby socket receives the union via the exclude=None broadcast.
- `test_emit_event_emitter_absent_supplier_returns_clear_not_union` — `emit_event` returns the canonical union as the emitter frame when the supplier yields None for them.

Green guards (correct now; the fix must keep them green):
- `test_dice_midturn_opposed_check_emits_no_confrontation_to_any_socket` — opposed_check defers; no mid-turn emit (mid-turn frames isolated via narrator-call-time capture, so the legitimate post-narration emit is not flagged).
- `test_dice_path_post_narration_emit_still_fans_out_to_seated_peer` — the post-narration emit stays ADDITIVE and reaches the seated peer.

### Rule Coverage

`.pennyfarthing/gates/lang-review/python.md` is a **Dev-side production-code** self-review checklist (13 checks: silent exceptions, mutable defaults, path/resource/deserialization handling, input validation, dependency hygiene, etc.). Those target the implementation Dev writes, not RED test authoring. The two checks that bind test design:

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 Test quality (no vacuous assertions) | self-check across all 7 tests — every test asserts concrete frame counts, beat-id sets, span attrs, or momentum equality; no `assert True`/truthy-only/always-None | pass |
| #9 Async pitfalls | all async tests `await handle_message`; AsyncMock side_effects are coroutines and awaited by the mock; `asyncio.Queue` used without blocking calls | pass |

**Rules checked:** 2 of 2 test-applicable lang-review checks have coverage; the other 11 are Dev-side production checks for the GREEN diff.
**Self-check:** 0 vacuous tests found.

**Dev guidance (GREEN):**
- The dice mid-turn emit (`dispatch/dice.py:712-785`) must call the SAME `emit_event(per_recipient_payload=...)` supplier 59-16 used at `websocket_session_handler.py:1638-1692` (mirror `_confrontation_frame_for`: `(None, actor)` → fail-loud span + None; `(None, None)` → None; else filtered payload). `dispatch_dice_throw` has no handler ref — thread the emit through a callback from `handlers/dice_throw.py` (which holds the handler) OR move the mid-turn emit up into the handler. Delete `room_broadcast(union)` + the overlay loop + the now-unused `connected_player_ids`/`per_recipient_emit` callbacks if nothing else uses them.
- Scope item (2): dedupe `connect.py:1542-1568` resume to call the shared supplier (it currently passes `recipient_pc=None` straight into `build_confrontation_payload` on an unresolvable seat → builds the UNION for that resumer — a latent leak the shared supplier closes). See AC3 deviation.
- Scope item (3): `emitters.emit_event` emitter-absent fallback (≈405-412) and legacy-no-EventLog fallback (≈638-650) must return a clear/empty frame, never `payload_model` (the union). `test_emit_event_emitter_absent_supplier_returns_clear_not_union` pins the per-recipient-branch case.
- Add OTEL on the new emit site (CLAUDE.md OTEL principle) — reuse `encounter_momentum_broadcast_span` + `confrontation_recipient_unresolved_span`.

**Handoff:** To Dev (Inigo Montoya) for implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/dispatch/confrontation.py` — NEW `make_confrontation_frame_supplier(...)`: the shared per-recipient supplier (fail-loud `confrontation.recipient_unresolved` span on a seated-unresolvable PC, `None` for unseated, class-filtered payload otherwise). Single source of truth for the three call sites.
- `sidequest/server/dispatch/dice.py` — mid-turn CONFRONTATION block now routes through a new `emit_confrontation(union_payload, supplier)` callback (the handler's `emit_event` seam) when provided; falls back to a single union `room_broadcast` for bare-dispatch callers. Deleted the Story-49-7 union-broadcast + per-PC overlay loop. Signature: dropped `connected_player_ids`/`per_recipient_emit`, added `emit_confrontation`.
- `sidequest/handlers/dice_throw.py` — wires `emit_confrontation` → `session._emit_event("CONFRONTATION", union, per_recipient_payload=supplier)`; removed the overlay callback plumbing.
- `sidequest/server/websocket_session_handler.py` — post-narration path (59-16) now calls the shared `make_confrontation_frame_supplier` instead of an inline `_confrontation_frame_for` (DRY; behavior identical).
- `sidequest/server/emitters.py` — NEW `_clear_confrontation_like(...)`; the MP per-recipient emitter-absent fallback now returns a cleared frame, never the canonical union. (Legacy/solo path keeps `payload_model` — see Dev deviation.)
- `sidequest/handlers/connect.py` — resume path uses the shared supplier; an unresolvable/unseated resumer no longer bootstraps the 16-button union (closes a latent leak). Removed now-unused `ConfrontationPayload` import.

**Tests:** Full server suite — 8718 passed, 360 skipped, 6 failed. All 6 failures are PRE-EXISTING content-tree gaps unrelated to this change (`test_pack_validator*` content/cross-ref lint + `test_audit_namegen_corpora` — epic-64 territory, see [[project_epic59_61_stale_premises]] / epic 64 backlog). The 7 new 59-20 tests + the 7 `test_confrontation_dispatch_wiring` tests + 59-16 sibling + momentum-span + space_opera SWN e2e + HP e2e + dogfight roundtrip all GREEN.
**Lint:** `ruff check` clean on all changed files.
**Types:** `pyright` — 0 NEW errors in the changed core files (confrontation.py/dice.py/dice_throw.py: the single error is pre-existing in the untouched dogfight branch; emitters.py 958/967 are the pre-existing object-typed fan-out).
**OTEL:** preserved — `encounter_momentum_broadcast_span` still wraps the mid-turn emit; `confrontation.recipient_unresolved` now fires from the shared supplier at all three sites; `emit.author_resolved` unchanged.
**Branch:** feat/59-20-route-dice-midturn-single-supplier (pushed)

**Handoff:** To verify (Fezzik) / review (Westley).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (one Minor spec-narrowing, already logged + resolved)
**Mismatches Found:** 1

AC-by-AC against `context-story-59-20.md`:
- **AC1** (dice mid-turn → single supplier; union deleted) — MATCH. `dice.py` routes the non-opposed mid-turn emit through the handler's `emit_confrontation` → `emit_event(per_recipient_payload=...)`; the union `room_broadcast` + per-PC overlay loop are deleted. Bare-dispatch callers retain a single union `room_broadcast` (capability fallback, mirrors the prior `connected_player_ids is not None` gating — not a new silent fallback).
- **AC2** (fail-loud seated-unresolvable; skip unseated) — MATCH. `make_confrontation_frame_supplier` fires `confrontation.recipient_unresolved` on `(None, actor)` and returns `None` on `(None, None)`; `emit_event` skips `None` recipients.
- **AC3** (connect.py resume shares supplier) — MATCH. Resume calls the shared supplier and appends only non-None frames; the prior latent `recipient_pc=None → union` resume leak is closed.
- **AC4** (LOW: emitter-absent fallback returns clear, not union) — PARTIAL by design (see mismatch below).

- **AC4 applied to the MP per-recipient branch only, not the legacy/solo branch** (Different behavior — Behavioral, Minor)
  - Spec: scope item (3) says both the per-recipient and the legacy-no-EventLog fallbacks return a clear frame instead of the union.
  - Code: only the MP per-recipient branch returns a clear frame; the legacy/solo branch keeps `payload_model`.
  - Recommendation: **A — update spec.** The implementation revealed the legacy branch's `out_to_self` is delivered to a SINGLE socket (solo / non-slug connect) — there is no peer to leak to, so returning the player's own full confrontation is correct, not a firewall hole. Forcing a clear frame there unmounts the solo tab and broke three pre-existing post-narration wiring tests (ground truth that the solo frame must stay populated). The firewall surface the spec actually cares about is the per-recipient branch, which is now fixed and pinned by `test_emit_event_emitter_absent_supplier_returns_clear_not_union`. Logged as a Dev deviation; no code change needed.

**Decision:** Proceed to verify (Fezzik). The single mismatch is a correct, intentional spec-narrowing with a logged deviation — no hand-back to Dev.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (confrontation.py, dice.py, dice_throw.py, emitters.py, websocket_session_handler.py, connect.py)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | `make_confrontation_frame_supplier` correctly consolidates the per-recipient logic across all 3 call sites; no new duplication. |
| simplify-quality | 5 findings (3 medium, 2 low) | type annotation `Any`→`ConfrontationPayload\|None` (APPLIED); docstring/comment clarifications + a local-var shadow note (flagged). |
| simplify-efficiency | 3 findings (2 medium, 1 low) | unify the emit_confrontation callback / pass handler into dispatch (DECLINED — see below); inline `_clear_confrontation_like` (noted). |

**Applied:** 1 — tightened `make_confrontation_frame_supplier` (and its inner `_frame_for`) return type from `Callable[[str], Any]` to `Callable[[str], ConfrontationPayload | None]` via a `TYPE_CHECKING` import. Pre-empts the type-design reviewer; ruff + pyright clean, 20 affected tests green. Committed `e1abb2e4`.

**Flagged for Review (medium):**
- dice.py: document the mutual-exclusivity of `emit_confrontation` (production) vs `room_broadcast(union)` (bare-dispatch fallback) in the docstring.
- dice_throw.py: add a comment that `_emit_confrontation` is only invoked for non-opposed beats (opposed defers to narration_apply).
- emitters.py: extend the `per_recipient_payload` docstring to mention the `_clear_confrontation_like` emitter-absent fallback.

**Declined (with rationale):**
- efficiency #1/#2 (move `emit_event` into `dispatch_dice_throw` / pass the handler in, dropping the callback): rejected by design. `dispatch_dice_throw` is deliberately handler-agnostic (it takes plain callbacks, not the `WebSocketSessionHandler`); coupling it to the handler would entangle the dispatch layer with the websocket layer and break the bare-dispatch e2e fixtures (`test_space_opera_swn_combat_e2e`, `test_space_opera_hp_e2e`) that drive it with only `room_broadcast`. The callback indirection is the seam that keeps those layers decoupled.

**Noted (low):**
- dice_throw.py local `room_broadcast` shadows the dispatch param name (intentional wrapper; pre-existing pattern).
- emitters.py `_clear_confrontation_like` is a small factory — kept as a named function for the two-site contract clarity (per-recipient branch + the documented intent), not inlined.

**Quality Checks:** ruff clean; pyright 0 errors on changed core files (pre-existing errors only, untouched code); full server suite 8718 passed / 6 pre-existing content-tree failures (epic-64) / 0 regressions.
**Overall:** simplify: applied 1 fix
**Handoff:** To Reviewer (Westley) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (25 focused tests GREEN, ruff clean, pyright delta 0) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 (low) | confirmed 1 (pre-existing, non-blocking), dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 enabled returned; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 1 confirmed (LOW, pre-existing, logged as non-blocking delivery finding), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

### Rule Compliance

- **No Silent Fallbacks (CLAUDE.md)** — enumerated every CONFRONTATION delivery decision in the diff:
  - `make_confrontation_frame_supplier._frame_for` (confrontation.py) — `(None, actor)` fires `confrontation.recipient_unresolved` ERROR span + returns None; `(None, None)` returns None (unseated, legitimately silent); else filtered payload. COMPLIANT.
  - `emitters.emit_event` MP per-recipient branch — union persisted to EventLog via `tx.append_event`; each socket gets `supplier(pid)` or is skipped; the union `payload_model` is never enqueued to a socket. The emitter-absent fallback returns `_clear_confrontation_like` (cleared frame), never the union. COMPLIANT.
  - `emitters.emit_event` legacy/solo branch — returns `payload_model` only on the single-socket path (no peer to leak to). COMPLIANT (intentional, see deviation audit).
  - `dice.py` mid-turn — `emit_confrontation` (prod) routes through the supplier; `room_broadcast(union)` only on the `elif` when no handler emit is wired (bare-dispatch e2e). COMPLIANT.
- **OTEL on every subsystem decision (CLAUDE.md)** — `encounter_momentum_broadcast_span` still wraps the mid-turn emit; `confrontation.recipient_unresolved` now fires from the shared supplier at all three sites; `emit.author_resolved` unchanged; `confrontation_resume_emitted` retained on the connect path. COMPLIANT (one duplicate-span nit, LOW — see findings).
- **No Source-Text Wiring Tests (sidequest-server/CLAUDE.md)** — the new tests assert on delivered frames on real socket queues + OTEL spans, never `read_text()` of source. COMPLIANT.
- **Type design (verify-applied)** — `make_confrontation_frame_supplier` returns `Callable[[str], ConfrontationPayload | None]`, not `Any`. COMPLIANT.

### Observations

- `[VERIFIED]` Union never reaches a client socket on the MP path — `emitters.py:390-417` persists the union via `tx.append_event` then enqueues only `_frame_for(pid)` (filtered or skip). Confirmed by reviewer-security (instances_checked=2, violations=0).
- `[VERIFIED]` Fail-loud on seated-unresolvable — `confrontation.py` `_frame_for` opens `confrontation_recipient_unresolved_span` and returns None; pinned by `test_dice_midturn_seated_unresolvable_fails_loud_no_union`.
- `[VERIFIED]` Shared supplier is the single source of truth across all 3 sites (dice mid-turn, post-narration, connect resume) — `confrontation.py:317`, called from `dice.py`, `websocket_session_handler.py:1646`, `connect.py`. reviewer-simplify-reuse (verify) confirmed no duplication.
- `[VERIFIED]` connect.py resume no longer bootstraps the union for an unresolvable/unseated resumer — replaced `recipient_pc=None → build_confrontation_payload(union)` with the supplier; a reconnecting player resolves per their own `player_id`.
- `[VERIFIED]` Opposed-check still defers (no mid-turn emit) and the post-narration emit stays additive — `test_dice_midturn_opposed_check_*` + `test_dice_path_post_narration_emit_still_fans_out_to_seated_peer` green.
- `[LOW][SEC]` Duplicate `confrontation.recipient_unresolved` span when a seated-unresolvable PC is also the emitter — `emitters.py:402-432`. The loop sets `emitter_msg=None` for the unresolvable emitter, then the fallback re-invokes the supplier, firing the span twice. **Pre-existing from Story 59-16** (the loop+fallback structure predates this change; 59-20 only swapped the fallback payload union→clear). No data leak — the cleared frame is returned, never the union. GM-panel observability only. Logged as a non-blocking delivery finding.

### Devil's Advocate

Suppose this code is broken. The scariest failure mode for a perception-firewall change is a union frame reaching a peer socket — a player seeing another class's combat beats, or worse, hidden state. Could a race do it? The mid-turn emit now runs through `emit_event`, which appends the union to the EventLog inside a transaction *before* any socket send, then fans `supplier(pid)` per recipient. A reconnect racing the emit would, in the worst case, miss the live frame and rebuild from the EventLog on resume — but resume now also runs the *same* supplier, so the rebuilt frame is class-filtered too. The old bug (union via `room_broadcast` racing the overlay) is structurally gone: there is no second union write to any queue. What about the bare-dispatch `room_broadcast(union)` fallback — could production hit it? Only if `session._room is None` at the dice site, in which case `dice_throw.py` never builds `emit_confrontation`; but a slug-connected production session always has a room, so the fallback is dev/test-only. A confused operator running a legacy single-socket fixture would see the union — acceptable, it's one socket, no peer. What if `genre_pack.classes` is empty or the resuming player's class was renamed? Then `resolve_recipient_pc` returns `(None, actor)` → fail-loud span + no frame: the player sees no confrontation tab rather than a leaked union. That's the correct, conservative failure. What about a stressed filesystem / DB? The union append is transactional; a crash rolls back the event and no partial frame is sent. The one genuine wart the devil found — the double-span — is observability noise, not a breach, and it predates this story. I cannot construct a leak path. The firewall holds.

**Data flow traced:** player DICE_THROW → `dice_throw.handle_message` → `dispatch_dice_throw` (applies beat, broadcasts dice msgs) → `emit_confrontation(union, supplier)` → `handler._emit_event` → `emitters.emit_event` (union→EventLog; `supplier(pid)`→each socket; None→skip) → peer sockets receive only their class-filtered frame. Safe: the union is never enqueued to a client socket on the MP path.

**Handoff:** To SM for finish-story.

## Delivery Findings

<!-- marker: append findings below, never edit another agent's entries -->

### TEA (test design)
- **Improvement** (non-blocking): three sibling test files (`test_confrontation_single_delivery.py:32,165`, `test_dogfight_player_throw_roundtrip.py:231`, `test_confrontation_mp_broadcast.py:23`) reference the deleted `test_dice_throw_confrontation_emit.py` by name in prose comments ("see the pattern in X"). The pattern now lives in `test_dice_midturn_single_delivery.py`. Left unedited to avoid cross-file churn in RED. *Found by TEA during test design.*
- **Question** (non-blocking): the dice mid-turn block carries a stale comment ("Sebastien's lie-detector", `dispatch/dice.py:716`) — per the playgroup rubric this is a Keith/dev OTEL concern, not a Sebastien-facing feature. Worth correcting when Dev rewrites that block. Affects `sidequest/server/dispatch/dice.py` (comment only). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): resolved the TEA "Sebastien's lie-detector" comment — the rewritten mid-turn block in `dispatch/dice.py` no longer carries it. The three stale prose references to the deleted `test_dice_throw_confrontation_emit.py` in sibling test files remain (left to avoid cross-file churn; harmless). *Found by Dev during implementation.*
- **Improvement** (non-blocking): the bare-`dispatch_dice_throw` union `room_broadcast` fallback is exercised only by e2e fixtures that don't wire the handler emit (`test_space_opera_swn_combat_e2e`, `test_space_opera_hp_e2e`). In production the handler always supplies `emit_confrontation`, so the fallback is effectively dev/test-only — a future cleanup could move those e2e tests onto the real-room harness and drop the fallback. Affects `sidequest/server/dispatch/dice.py`. *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking): simplify-quality flagged three doc clarifications worth a Reviewer pass — (1) `dice.py` docstring should state `emit_confrontation` (prod) and `room_broadcast(union)` (bare-dispatch) are mutually exclusive; (2) `dice_throw.py` `_emit_confrontation` should note it only fires for non-opposed beats; (3) `emitters.py` `per_recipient_payload` docstring should mention the `_clear_confrontation_like` emitter-absent fallback. Comments only, no behavior. *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): `emitters.emit_event` fires `confrontation.recipient_unresolved` TWICE for a seated-unresolvable PC that is also the emitter — the per-recipient loop sets `emitter_msg=None` and the emitter-absent fallback then re-invokes the supplier. PRE-EXISTING from Story 59-16 (the loop+fallback structure predates 59-20; this story only changed the fallback payload union→clear). No data leak — the cleared frame is returned, never the union; GM-panel observability noise only. Fix: cache the emitter's loop result instead of re-calling the supplier in the fallback. Affects `sidequest/server/emitters.py:402-432`. *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- **AC3 (connect.py resume) covered by deviation, not a new behavioral test**
  - Spec source: context-story-59-20.md, AC3 / scope item (2)
  - Spec text: "dedupe handlers/connect.py:1515-1568 resume against the same supplier (already single-filtered; just share the helper)"
  - Implementation: No standalone reconnect-driven test was written for the resume path. The resume path is already single-filtered for the common case (delivered only to the resuming socket via `bootstrap_msgs`, not broadcast), and driving the full reconnect handler (saved snapshot + bootstrap flow) is disproportionate for a pure helper-extraction. The shared supplier's behavior is pinned by the dice-path AC1/AC2 tests; the latent resume union-leak on an unresolvable seat is documented in Dev guidance.
  - Rationale: right-size test ceremony to a refactor sub-item; avoid a heavy reconnect harness when the shared seam is already behaviorally pinned elsewhere.
  - Severity: minor
  - Forward impact: if Dev's refactor changes resume delivery semantics, add a reconnect behavioral test in verify.
- **Two tests are green at RED (invariant guards), not failing**
  - Spec source: context-story-59-20.md, AC1 negative + AC5 (additive)
  - Spec text: "opposed_check defers"; "the post-narration emit at _execute_narration_turn MUST still fire"
  - Implementation: `test_dice_midturn_opposed_check_emits_no_confrontation_to_any_socket` and `test_dice_path_post_narration_emit_still_fans_out_to_seated_peer` pass against current code — they pin invariants the single-supplier refactor must preserve (regression guards), not behavior that changes.
  - Rationale: a delivery-consolidation story needs guards against over-emitting on the opposed branch and against accidentally replacing (rather than supplementing) the post-narration emit.
  - Severity: minor
  - Forward impact: none — both must stay green through GREEN/verify.
- **Retired test_dice_throw_confrontation_emit.py rather than converting in place**
  - Spec source: story scope — "reconcile tests/server/test_dice_throw_confrontation_emit.py (... convert to the real-room harness)"
  - Spec text: "a momentum-sync test on a _StubRoom — needs seating + a class injected, or convert to the real-room harness"
  - Implementation: the stub-room tests' contracts (single mid-turn frame, before-narration ordering, post-apply momentum, opposed-defer, AC5 fan-out) were migrated to the seated real-room harness in the new file and the old file was deleted, rather than rewritten in place.
  - Rationale: converting in place would duplicate the new file's coverage; the stub-room AC5 peer was unseated and would break post-fix regardless. Delete-and-migrate keeps the suite DRY.
  - Severity: minor
  - Forward impact: none.

### Dev (implementation)
- **emitters.py clear-frame fix applied to the MP per-recipient branch only, NOT the legacy/solo branch**
  - Spec source: story scope item (3) (session Scope; TEA Dev-guidance line)
  - Spec text: "the emitter-absent / legacy-no-EventLog fallbacks (emitters.py:391-397, 625-632) return the canonical union as out_to_self when the emitter can't be identified — return an empty/clear frame instead"
  - Implementation: only the MP per-recipient branch (event_log present, multi-socket fan-out) returns a cleared frame when the supplier yields None for the emitter. The legacy/no-EventLog branch still returns `payload_model` (the canonical confrontation) for the emitter's own outbound.
  - Rationale: the legacy branch's `out_to_self` is delivered to a SINGLE socket (solo / non-slug connect) — there is no peer socket to leak to, so it is not a firewall surface. Returning a cleared frame there unmounts the solo player's confrontation tab and broke three pre-existing post-narration wiring tests (`test_confrontation_dispatch_wiring.py::{test_confrontation_message_refreshed_on_live_to_live, test_dice_turn_filters_only_rolling_actor_beat_selection, test_dice_turn_success_applies_opponent_beat_selections}`) whose minimal harness has an unseated emitter and reads the returned frame as the player's view. Those tests are ground truth that the solo post-narration frame must stay populated. The real cross-player firewall (the spec's intent) is the per-recipient branch, which `test_emit_event_emitter_absent_supplier_returns_clear_not_union` pins.
  - Severity: minor
  - Forward impact: none — the union never reaches a *peer* socket (the firewall invariant holds); the solo emitter's own full view is by design.
- **AC3 resume implemented via the shared supplier (no new standalone test) — consistent with the TEA AC3 deviation**
  - Spec source: context-story-59-20.md, AC3 / scope item (2)
  - Spec text: "dedupe handlers/connect.py:1515-1568 resume against the same supplier"
  - Implementation: `connect.py` resume now calls `make_confrontation_frame_supplier(...)` and appends only a non-None frame; an unresolvable/unseated resumer gets the fail-loud span + no union (latent-leak fix). Covered by the existing connect/resume suite staying green (no new behavioral reconnect test, per the TEA AC3 deviation rationale).
  - Rationale: the shared supplier is behaviorally pinned by the dice-path AC1/AC2 tests; a dedicated reconnect harness remains disproportionate for a helper-extraction.
  - Severity: minor
  - Forward impact: none.

### Reviewer (audit)
- TEA "AC3 covered by deviation, not a new behavioral test" → ✓ ACCEPTED by Reviewer: the shared supplier is behaviorally pinned by the dice-path AC1/AC2 tests; the connect/resume suite stays green. A reconnect harness is disproportionate for a helper-extraction.
- TEA "Two tests green at RED (invariant guards)" → ✓ ACCEPTED by Reviewer: opposed-defer + additive-post-narration are exactly the invariants a delivery-consolidation must guard; both remain green through GREEN/verify.
- TEA "Retired test_dice_throw_confrontation_emit.py rather than converting in place" → ✓ ACCEPTED by Reviewer: contracts migrated to the seated real-room harness; the stub-room AC5 peer was unseated and would have broken post-fix. Delete-and-migrate is DRY.
- Dev "AC4 clear-frame fix applied to MP per-recipient branch only, not legacy/solo" → ✓ ACCEPTED by Reviewer: the legacy branch delivers to a single socket (no peer to leak to); forcing a clear frame there unmounts the solo tab and broke three pre-existing wiring tests. The firewall surface is the per-recipient branch, which is fixed and tested. Agrees with the Architect spec-check Option-A resolution.
- Dev "AC3 resume implemented via the shared supplier (no new standalone test)" → ✓ ACCEPTED by Reviewer: consistent with the TEA AC3 deviation; closes the latent resume union-leak on an unresolvable seat.
- No undocumented deviations found by Reviewer.

### Architect (reconcile)

Reviewed all in-flight entries (TEA ×3, Dev ×2) against `context-story-59-20.md`, the spec `docs/superpowers/specs/2026-05-26-confrontation-single-filtered-delivery.md` §Implementation step 3, and sibling epic-59 ACs. All five entries have complete, accurate 6-field content; spec quotes verified against the context file; implementation descriptions match the merged code. No corrections required. One deviation was logged only as a delivery *finding* and is formalized here:

- **`room_broadcast(union)` retained as a bare-dispatch fallback rather than fully deleted**
  - Spec source: context-story-59-20.md, Scope item (1) / spec §Implementation step 3
  - Spec text: "Route dice mid-turn through the same emit_event supplier and DELETE room_broadcast(union) + the overlay loop"
  - Implementation: the per-PC overlay loop is fully deleted and the PRODUCTION mid-turn path no longer union-broadcasts (it routes through `emit_event(per_recipient_payload=...)` via `emit_confrontation`). However `dispatch_dice_throw` retains a single `room_broadcast(ConfrontationMessage(union))` on the `elif room_broadcast is not None` branch, reachable only when no handler `emit_confrontation` is wired (bare-dispatch e2e/legacy single-socket fixtures: `test_space_opera_swn_combat_e2e`, `test_space_opera_hp_e2e`).
  - Rationale: `dispatch_dice_throw` is deliberately handler-agnostic (it takes plain callbacks, not the `WebSocketSessionHandler`); keeping a `room_broadcast` capability path preserves that layer boundary and the existing e2e fixtures. In a slug-connected production session `session._room` is always present, so the handler always supplies `emit_confrontation` and the union fallback is unreachable in real multiplayer play — no peer-leak path (single socket only when it fires). Confirmed by reviewer-security (instances_checked, violations=0).
  - Severity: minor
  - Forward impact: a future cleanup (noted as a Dev delivery finding) could migrate those e2e fixtures onto the real-room harness and drop the fallback entirely, fully satisfying the literal "DELETE room_broadcast(union)" wording.

- AC accountability: no ACs were deferred or descoped — AC1/AC2/AC3 fully implemented and tested; AC4 (LOW) implemented on the firewall-relevant MP per-recipient branch (the legacy/solo narrowing is the logged Dev deviation, Architect-accepted at spec-check). The one open follow-up (Reviewer's LOW duplicate-`recipient_unresolved`-span nit) is PRE-EXISTING from 59-16, non-blocking, and tracked as a delivery finding — not a 59-20 regression.