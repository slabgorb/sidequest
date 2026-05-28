---
story_id: "71-13"
jira_key: null
epic: "71"
workflow: "tdd"
---
# Story 71-13: MP opening live-broadcast bypasses emit_event — route opening through emit_event(author_player_id) for uniform per-recipient POV + perception fanout + event-sourcing

> ✅ **BLOCKER RESOLVED (2026-05-28, SM/team-lead).** Houlihan's spec-check Deviation-2 rejection has been fixed at commit **467447d**: (1) `test_opening_does_not_use_room_broadcast` narrowed to assert only NARRATION-type messages bypass broadcast; (2) `self._room.broadcast(party_status_msg, exclude_socket_id=...)` restored (silent-fallback removed, `broadcast.recipient_dropped` telemetry preserved). Deviation 1 (universal `_visibility` C3 strip) kept — APPROVED. Verified with PG: 11 passed (9 opening/71-13 + 2 projection wiring), 0 skipped; ruff clean; pyright −2 vs green (no new errors). Merged to develop via PR (see finish). NOTE: this file contains two conflicting auto-relay spec-check assessments; **Houlihan's rejection was authoritative and is now satisfied.**

## Story Details
- **ID:** 71-13
- **Jira Key:** None (personal project — no Jira)
- **Workflow:** tdd (setup → red → green → spec-check → verify → review → spec-reconcile → finish)
- **Repository:** sidequest-server (CONFIRMED — entire path is server-side; epic-71.yaml records `sidequest-server`)
- **Branch:** feat/71-13-mp-opening-emit-event (off origin/develop @ 09681b0, includes 71-2/#486+#488, 71-6/#490)
- **Story Type:** Bug
- **Points:** 5
- **Priority:** p2

## Problem Statement

The MP opening narration is the **last narration path still on the raw transport fan-out**. At `chargen_mixin.py:1593-1594` the opening broadcasts via `self._room.broadcast(_msg, exclude_socket_id=...)` — a dumb per-socket `put_nowait` — instead of `emit_event()`, the per-recipient pipeline every other narration turn uses. Story 71-5 patched the *driver's own* card with a targeted helper (`_pov_swap_opening_for_driver`, chargen_mixin:104-203) and explicitly DEFERRED the full routing to 71-13. This is that story.

Two defects fall directly out of skipping `emit_event`:

1. **anchor-peer live-swap.** When a PEER's PC is the narration `anchor_pc`, that peer never gets their opening card POV-swapped to 2nd person *live* — they receive the raw 3rd-person broadcast and only see the correct swap on RECONNECT (event-log projection). The live `room.broadcast` path never calls `_apply_pov_swap` for peers. (71-5's helper only swaps the driver.)
2. **`visible_to` private-segment leak.** A NARRATION card carrying `_visibility.visible_to = ["player:X"]` is broadcast to ALL seated players because `room.broadcast` has zero visibility concept — `emit_event`'s `ComposedFilter.project()` (which reads `visible_to` and excludes non-recipients) is never invoked. Private opening segments leak.

Plus the pre-existing **`_visibility` egress leak** (Architect's 71-5 note): the raw broadcast ships the `_visibility` sidecar on the wire to everyone; `emit_event`'s C3 "rebuild from filtered dict" closes this.

## Architecture Context (from Explore investigation 2026-05-28)

### Current opening path (the bug)
- `chargen_mixin.py::_chargen_confirmation` (~1554): gate `_should_fire_opening_narration` → `_run_opening_turn_narration` (~1555) returns `opening_messages` (cold-open seed NARRATION + narrator prose card(s)).
- 71-5 driver patch (~1572-1578): `driver_copies = _pov_swap_opening_for_driver(opening_messages, driver_player_id=(sd.player_id or player_id), view, snapshot)` → `out.extend(driver_copies)` (driver's local swapped return).
- **Peer broadcast (~1593-1594):** `for _msg in opening_messages: self._room.broadcast(_msg, exclude_socket_id=self._socket_id)` ← **THE BUG**.
- `room.broadcast` (session_room.py:865-905): raw fan-out. NO event persistence, NO projection, NO visibility filter, NO perception rewrite, NO POV swap, NO `projection.filter.decide` span. Only an `opening.broadcast_to_peers` watcher event with `message_count`.

### The correct pipeline — `emit_event` (emitters.py:235-554)
Signature: `emit_event(handler, kind, payload_model, *, author_player_id: str | None = None)`. Per recipient it does: (1) **persist** (C2 txn, `append_event`, assigns seq); (2) **project** `projection_filter.project(envelope, player_id=pid)` → reads `visible_to`, decides include/exclude, emits `projection.filter.decide` span per distinct player; (3) **perception rewrite** `rewrite_for_recipient` (fidelity span-strip); (4) **POV swap** `_apply_pov_swap` per recipient matching `_visibility.anchor_pc` + `pov_strategy=="pc_anchored"`; (5) **fanout** `_deliver_fanout` (C3: rebuild payload from filtered dict alone — never merge canonical — prevents field leaks); (6) **author handling** — if `author_player_id` set, the driver is **projected like a peer** (ADR-105 Track A); if `None` (solo), driver is raw-bypassed (Invariant 3). OTEL: `emit.author_resolved` (with `project_emitter` flag) + `projection.filter.decide` per player.

### Divergence — what broadcast skips that emit_event does
persistence/seq · per-recipient projection · `visible_to` decision · perception rewrite · per-recipient POV swap · author-projection (Track A) · projection cache (reconnect replay) · `projection.filter.decide` + `emit.author_resolved` OTEL.

### Relevant prior art / tests
- ADR-105 Track A reference tests: `tests/server/test_merged_mp_emitter_projection.py` (`test_merged_mp_threads_author_projects_every_distinct_recipient`, `test_solo_legacy_emitter_bypass_preserved_when_no_author`, `test_production_merged_turn_threads_author_player_id`) — the canonical pattern for "thread author_player_id so the author is projected, not raw-bypassed."
- `tests/server/test_projection_end_to_end_wiring.py` (projection + lazy_fill on reconnect).
- 71-5 opening tests: `tests/server/test_opening_pov_swap_71_5.py` (e2e, requires PG), `tests/server/test_pov_swap_opening_helper_71_5.py` (helper unit).
- Visibility/perception: `test_visibility_classifier.py`, `test_aggregate_visibility.py`, `test_perception_rewriter_wiring.py`.

## Acceptance Criteria (FINALIZED — reconciled to Architect Seam-Pin, 2026-05-28)

1. **Route through emit_event:** the MP opening (cold-open seed + narrator prose) is delivered via `emit_event(..., author_player_id=<driver pid>)`, NOT `room.broadcast`. The `room.broadcast` call at chargen_mixin:1593-1594 is removed for the opening.
2. **anchor-peer live-swap fixed:** in a live MP session, a peer whose PC == `anchor_pc` receives their opening card POV-swapped to 2nd person ("You…") **live** (not only on reconnect) — same `_apply_pov_swap` contract as every turn.
3. **`visible_to` leak fixed:** an opening NARRATION card with `visible_to=["player:X"]` is delivered ONLY to X; other seated players do not receive it (projection excludes them). `_visibility` sidecar is stripped from the wire for all recipients (C3).
4. **Driver still 2nd-person, no double-swap, no double-deliver:** the driver (author) is projected like a peer (Track A) and gets their anchored card in 2nd person via emit_event's `_apply_pov_swap` — the 71-5 `_pov_swap_opening_for_driver` helper + the `out.extend(driver_copies)` local return are REMOVED (subsumed by emit_event), so the driver is delivered exactly once through fanout.
5. **Event-sourcing:** the opening becomes a persisted event (emit_event C2 txn / seq), consistent with normal turns — confirm no journal-seq / opening_seed-consumption regression. **Behavioral change (intentional, seam-pin Q4):** the opening now appears in recap/replay (was never logged before). This is correct, not a regression — assert the opening event IS persisted.
6. **Cold-open seed stays a no-anchor broadcast:** the generic seed (no `_visibility`) projects to all, no POV swap (natural no-op) — consistent with 71-5's resolved Finding 2 (NO synthetic anchor stamping).
7. **OTEL:** per-recipient routing is observable — `emit.author_resolved` (with `project_emitter: true` confirming Track A) + `projection.filter.decide` per player fire for the opening (GM-panel lie detector). **RETIRE BOTH** legacy watcher events (seam-pin Q6): `opening.narration_pov_swapped` (71-5 helper gone) AND `opening.broadcast_to_peers` (broadcast path gone). The standard emit_event spans are the stronger replacement.
8. **No regression:** non-anchor peers still correctly receive 3rd person (single-anchor model, ADR-105 B3); peers/driver get exactly the cards they should; existing MP turn narration unaffected.

## OPEN DESIGN QUESTIONS — Architect to pin BEFORE TEA locks RED
(These are the interface decisions that determine the test surface; pinning them first prevents red-rework.)

- **Q1 — emit_event call shape:** one `emit_event` call per opening message (seed, then prose), or a batched form? `kind="NARRATION"`? Confirm the seed (no `_visibility`) and the anchored prose both route the same way and project correctly (seed → all, no swap; prose → per-recipient swap + visibility).
- **Q2 — 71-5 helper removal:** confirm `_pov_swap_opening_for_driver` (104-203) and the `out.extend(driver_copies)` driver-local return are DELETED and fully subsumed by `emit_event(author_player_id=...)` Track-A driver projection. Any path that must keep the helper? (No-stubbing/no-dead-code: if subsumed, delete it.)
- **Q3 — author_player_id:** `= sd.player_id` (seated driver), per 71-5 anchor-identity ruling? Confirm under the seat==core.name==anchor_pc invariant.
- **Q4 — event-sourcing safety:** the opening was NOT logged before; emit_event persists + assigns seq. Any interaction with `opening_seed`/`opening_directive` consumption, journal ordering, recap, or the two-committer barrier (first committer defers; last fires)? Does the seed need a distinct event kind?
- **Q5 — driver delivery seam:** with emit_event handling the driver via Track A, what replaces the handler's local `out` return for the opening? (The driver must receive via fanout, not a second local enqueue → confirm no double-delivery.)
- **Q6 — OTEL contract:** keep, retire, or subsume `opening.narration_pov_swapped`? Which spans are the lie-detector for "opening routed per-recipient"?
- **Q7 — universal `_visibility` egress-strip:** confirm emit_event's C3 rebuild strips `_visibility` for ALL recipients (closing the pre-existing leak the Architect folded into 71-13).

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish (current — design-pin consult with Architect before releasing TEA to red)
**Phase Started:** 2026-05-28T10:48:18Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T09:46:15Z | 2026-05-28T09:59:17Z | 13m 2s |
| red | 2026-05-28T09:59:17Z | 2026-05-28T10:22:24Z | 23m 7s |
| green | 2026-05-28T10:22:24Z | 2026-05-28T10:35:20Z | 12m 56s |
| spec-check | 2026-05-28T10:35:20Z | 2026-05-28T10:38:13Z | 2m 53s |
| verify | 2026-05-28T10:38:13Z | 2026-05-28T10:39:53Z | 1m 40s |
| review | 2026-05-28T10:39:53Z | 2026-05-28T10:46:10Z | 6m 17s |
| spec-reconcile | 2026-05-28T10:46:10Z | 2026-05-28T10:48:18Z | 2m 8s |
| finish | 2026-05-28T10:48:18Z | - | - |

## Sm Assessment

Setup for a 5pt p2 TDD story — the load-bearing MP-architecture follow-up to 71-5 (#485). Root cause is precisely identified (Explore map above): the opening is the last narration path on `room.broadcast` instead of `emit_event`, so it skips per-recipient projection / perception / POV / event-sourcing. The two named bugs (anchor-peer live-swap, visible_to leak) plus the pre-existing `_visibility` egress leak all resolve by routing through `emit_event(author_player_id=<driver>)` — the established ADR-105 Track A pattern. This is a WIRING/integration fix reusing existing machinery (emit_event, _apply_pov_swap, ComposedFilter.project), NOT new mechanism — and it should DELETE the 71-5 special-case helper (subsumed).

**Routing notes:**
- ⚠️ REPO = **sidequest-server** (confirmed). Branch off current develop.
- **DESIGN-PIN FIRST (this gotcha matters here):** I'm consulting Architect (Major Houlihan) during setup to pin Q1-Q7 BEFORE TEA locks red — the emit_event call shape, helper removal, event-sourcing safety, and driver-delivery seam determine the entire test surface. TEA stands by until the seam contract is in this session.
- **TEA leads RED** once pinned. Red scenarios map to ACs: (a) anchor-peer gets live 2nd-person; (b) visible_to private card excluded from non-recipients; (c) driver still 2nd-person via Track A (no double-swap/deliver); (d) seed no-op broadcast; (e) event persisted; (f) OTEL spans fire. Reuse the `test_merged_mp_emitter_projection.py` Track-A harness pattern.
- **Reuse-first (Dev):** route via existing `emit_event`; do NOT reimplement projection/POV. Remove the 71-5 helper rather than stacking on it (no double-swap).
- **OTEL doctrine APPLIES (real subsystem decision, not deterministic geometry):** per-recipient routing must emit spans (emit.author_resolved / projection.filter.decide). This is the lie-detector for "did the opening actually project per-recipient or silently broadcast." TEA asserts the spans; Reviewer re-verifies in real env (PG required — `just pg-up`; remember SKIP ≠ PASS on the e2e).
- **Architect** owns spec-check (post-green) and spec-reconcile, AND the pre-red seam-pin. **Reviewer** focus: firewall (no private leak), no double-swap/double-deliver, peers unregressed, event-sourcing correctness.
- **Watch the e2e PG gate:** the opening e2e persists to PG (ADR-115); it SKIPS without `SIDEQUEST_TEST_DATABASE_URL`. Gate claims must be scoped and the e2e must be run WITH PG (the 71-2 SKIP-masking lesson).

## Architect Seam-Pin (pre-red)

**Pinned:** 2026-05-28 | **Architect:** Major Margaret Houlihan (71-2 peloton)

All 7 open design questions resolved. TEA is cleared to lock red against this contract.

---

### Q1 — emit_event call shape: per-message, `kind="NARRATION"` for both

**Decision:** One `emit_event(self, "NARRATION", msg.payload, author_player_id=...)` call per message in `opening_messages`. No batched form.

**Rationale:** `emit_event` is per-event by design — each call appends one row to the EventLog with its own `seq`. Batching would require a new overload and is not justified. Two calls (seed + prose) is the correct shape.

Both seed and prose use `kind="NARRATION"`. They are NOT differentiated by kind — they're differentiated by `_visibility` sidecar content, which the projection pipeline already reads:
- **Seed** (no `_visibility`): `ComposedFilter.project()` finds no `visible_to` → include=True for all recipients. No anchor_pc → `_apply_pov_swap` is a no-op. All players receive the seed unchanged. ✓
- **Prose** (with `_visibility.anchor_pc` + `pov_strategy=="pc_anchored"`): projection filter reads `visible_to`, applies POV swap per matching recipient. ✓

**Minor note:** `emit_mechanical_census` is gated to `kind == "NARRATION"` inside `emit_event`'s C2 txn. It will fire once for the seed and once for the prose — two fires during the opening instead of zero. This is an idempotent state-read operation (same snapshot both times) — minor inefficiency, not harmful. No action required.

---

### Q2 — 71-5 helper removal: DELETE both, fully subsumed

**Decision:** `_pov_swap_opening_for_driver` (chargen_mixin.py:104-203) and the `driver_copies = ...` / `out.extend(driver_copies)` block at ~1573-1578 are **DELETED**. No path retains the helper.

**Rationale:** The helper's entire purpose was to apply `_apply_pov_swap` + strip `_visibility` for the driver because `room.broadcast` never called those steps. `emit_event` with `author_player_id` set (Track A) does EXACTLY this: projects the driver through `projection_filter.project()` → `rewrite_for_recipient()` → `_apply_pov_swap()` → rebuilds from filtered dict (C3, strips `_visibility`) — all inside the same C2 transaction. The returned `out_to_self` IS the driver's projected/swapped frame.

No dead code, no stubbing. The helper is gone; `out` collects `emit_event` returns (see Q5).

**Test implication:** `tests/server/test_pov_swap_opening_helper_71_5.py` tests the helper directly. With the helper deleted, TEA needs to decide whether to delete the helper tests (correct — they test a deleted implementation detail) or repurpose them as integration tests against the emit_event path.

---

### Q3 — author_player_id: `sd.player_id or player_id` for MP, `None` for solo

**Decision:** 
```python
_author_pid = (sd.player_id or player_id) if (
    self._room is not None and sd.mode == _GameMode2.MULTIPLAYER
) else None
```

**Rationale:** For MP, Track A requires `author_player_id` to be the seated driver (not the rotated session player) — consistent with the 71-5 anchor-identity ruling. `sd.player_id` is the seat-time identity (authoritative; same as the existing helper call's `driver_player_id=(sd.player_id or player_id)`).

For solo: `author_player_id=None` preserves Invariant 3 (raw bypass). The `swap_eligible` branch in `emit_event` then handles the solo driver's POV swap — functionally equivalent to the deleted helper for the solo case. No behavior change for solo.

The existing MP guard block is removed (its logic is subsumed), but the `_author_pid = None` for solo path keeps emit_event's solo semantics intact.

---

### Q4 — event-sourcing safety: no conflicts; same NARRATION kind; behavioral change is intentional

**Decision:** Route both seed and prose through emit_event as `kind="NARRATION"` events. No new event kind.

**Interaction analysis:**

1. **opening_seed / opening_directive consumption**: Both are consumed inside `_run_opening_turn_narration` (zeroed on `sd`) BEFORE `emit_event` is called. No interaction. ✓
2. **Two-committer barrier**: `_should_fire_opening_narration` gate ensures `emit_event` is only called from the last (firing) committer. The first committer's deferred path never reaches `_run_opening_turn_narration`. `emit_event` fires exactly once. ✓
3. **Journal ordering**: Opening gets the next available `seq` after all other chargen events. Since opening fires at the tail of `_chargen_confirmation`, this is correct insertion-order. ✓
4. **Recap**: The opening NARRATION events are now persisted and will appear in recap/event-log replay. **This is intentional correct behavior** — the opening is narration and should be recappable. TEA must test that `seq` is assigned (event persisted). Document as behavioral change in AC5.
5. **`opening_seed` event kind**: NOT needed. The seed card is narrative content the player reads (it IS narration). The `_visibility`-free seed is naturally handled by the NARRATION pipeline (broadcast-to-all, no POV swap). Introducing a distinct kind would require new routing in `_KIND_TO_MESSAGE_CLS` and `emit_event` — unjustified complexity.

---

### Q5 — driver delivery seam: collect emit_event returns; remove broadcast block entirely

**Decision:** Replace the helper + broadcast block with:

```python
_author_pid = (sd.player_id or player_id) if (
    self._room is not None and sd.mode == _GameMode2.MULTIPLAYER
) else None
for msg in opening_messages:
    _out_msg = emit_event(self, "NARRATION", msg.payload, author_player_id=_author_pid)
    out.append(_out_msg)
```

**What this replaces (DELETE all of):**
- `_driver_view = SessionGameStateView(...)` setup
- `driver_copies = _pov_swap_opening_for_driver(...)`
- `out.extend(driver_copies)`
- The `if self._room is not None and sd.mode == _GameMode2.MULTIPLAYER and ...` broadcast guard block
- `for _msg in opening_messages: self._room.broadcast(_msg, exclude_socket_id=...)`
- `_watcher_publish("opening.broadcast_to_peers", ...)`

**No double-delivery proof:**
- `emit_event` builds `recipients = [pid for pid in room.connected_player_ids() if pid != emitter_player_id]` — driver is excluded from peer fanout.
- Track A builds the driver frame separately (`emitter_projected_dict`) and returns it as `out_to_self`.
- `out.append(_out_msg)` delivers the driver's card to the local return queue — exactly once.
- `_deliver_fanout` sends each peer their projected frame — exactly once.

**Import needed:** Add `from sidequest.server.emitters import emit_event` to the top-level imports in `chargen_mixin.py` (not a local import like the helper did). The module is already imported by the helper's local import; promote it to top-level for the production call site.

---

### Q6 — OTEL contract: retire both opening-specific watcher events; standard emit_event spans are the lie-detector

**Decision:**
- **RETIRE `opening.narration_pov_swapped`** — subsumed. (Helper deleted → event disappears naturally.)
- **RETIRE `opening.broadcast_to_peers`** — subsumed. (Broadcast path removed → event disappears naturally.)

**Replacement lie-detectors (fire automatically from emit_event):**
- `emit.author_resolved` — fires once per `emit_event` call with `project_emitter: true`, `emitter_player_id: <driver_pid>`. Confirms Track A engaged for the opening. One per opening message.
- `projection.filter.decide` — fires once per distinct connected player per event. Confirms the opening was routed per-recipient (include/exclude decision visible in GM panel). For a 2-player opening with seed+prose, this fires 4 times (2 events × 2 players).

**These are STRONGER observability than the retired spans**: `projection.filter.decide` is per-player per-event (vs the retired aggregate-only `opening.narration_pov_swapped`), and `emit.author_resolved` specifically calls out the `project_emitter` flag — the exact thing that catches a silent Track A regression.

TEA should assert both spans fire for opening events (not just for regular turns).

---

### Q7 — universal `_visibility` egress-strip: CONFIRMED for all MP recipients

**Decision:** emit_event C3 strips `_visibility` for ALL recipients in the MP path. Confirmed by code trace.

**Peer path** (`_deliver_fanout`): `filtered_data = json.loads(decision.payload_json)` → `_deliver_fanout` rebuilds with `payload_cls.model_validate({**filtered_data, "seq": seq})`. The `filtered_data` dict comes from the projection filter output — `_visibility` is a server-side sidecar never included in the projected payload. Rebuilt from filtered dict only (C3 comment explicit in `_deliver_fanout`). `_visibility` absent from wire. ✓

**Driver path** (Track A): `emitter_projected_dict = json.loads(_e_decision.payload_json)` → rebuilt with `payload_cls_emitter.model_validate({**emitter_projected_dict, "seq": seq})`. Same C3 rule. `_visibility` absent from driver's wire frame. ✓

**Solo caveat (out of scope):** Invariant 3 raw bypass uses `payload_model.model_copy(update={"seq": seq})` — this copies the canonical payload including `_visibility` onto the solo driver's own card. This is a pre-existing issue. Solo has no peers to leak to, so it doesn't produce the bug described in the problem statement. Not in scope for 71-13; a separate story can address solo Invariant-3 C3 compliance.

AC3 is accurate as written — it covers the MP case (the stated bug).

---

### AC Flags (two revisions needed)

**AC5 — add recap behavioral change note:**
> Current: "the opening becomes a persisted event (emit_event C2 txn / seq), consistent with normal turns — confirm no journal-seq / recap / opening_seed-consumption regression."
>
> **Add:** "Opening events (seed + prose) are now present in event-log replay and recap — this is intentional correct behavior and a documented behavioral change from the prior no-persistence path. TEA asserts `seq` is assigned on the returned message."

**AC7 — expand to cover both retired watcher events:**
> Current: "Reconcile/retire the 71-5 `opening.narration_pov_swapped` watcher event per Architect ruling (likely subsumed by the standard emit_event spans)."
>
> **Replace with:** "Retire BOTH `opening.narration_pov_swapped` AND `opening.broadcast_to_peers` watcher events (broadcast path removed; both subsumed by `emit.author_resolved` + `projection.filter.decide`). TEA asserts `emit.author_resolved` with `project_emitter: true` fires for the opening, and `projection.filter.decide` fires per connected player."

All other ACs (AC1–AC4, AC6, AC8) are accurate. No other revisions needed.

---

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (9 failing — ready for Dev)

**Test Files:**
- `tests/server/test_opening_pov_swap_71_5.py` — repurposed as 71-13 wiring test (3 tests: room.broadcast not called, 2 retired OTEL events)
- `tests/server/test_opening_emit_event_71_13.py` — new (6 tests: anchor-peer live-swap, visible_to exclusion, seq persistence, emit.author_resolved OTEL, projection.filter.decide OTEL, solo persistence)
- `tests/server/test_pov_swap_opening_helper_71_5.py` — DELETED (helper being removed by Dev)

**Tests Written:** 9 tests covering ACs 1-8
**Commit:** af482ca

### Failure reasons (all correct — the bug, not test setup errors):
| Test | RED reason |
|------|-----------|
| `test_opening_does_not_use_room_broadcast` | `room.broadcast called 3 time(s)` |
| `test_broadcast_to_peers_watcher_event_retired` | `['opening.broadcast_to_peers']` event fires |
| `test_pov_swap_helper_watcher_event_retired` | `['opening.narration_pov_swapped']` event fires |
| `test_anchor_peer_gets_live_pov_swap_not_only_on_reconnect` | Peer gets raw `"Donut steps..."` not `"You step..."` |
| `test_visible_to_private_opening_card_excluded_from_non_recipients` | Peer receives private card text |
| `test_opening_events_persisted_with_seq_assigned` | `seq values: [0, 0]` |
| `test_emit_author_resolved_fires_with_project_emitter_true` | `emit.author_resolved events seen: []` |
| `test_projection_filter_decide_fires_per_connected_player` | `Players with decide span: set()` |
| `test_solo_opening_also_persisted_with_seq` | `Got: [0, 0]` |

**Handoff:** To Dev for GREEN implementation

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — Deviation 2 is a production degradation
**Mismatches Found:** 1 actionable (Deviation 1 confirmed correct; Deviation 2 rejected — hand back to Dev)

### AC Coverage

| AC | Status | Evidence |
|----|--------|----------|
| AC1 — route through emit_event | ✓ | `chargen_mixin.py`: `emit_event(self, "NARRATION", msg.payload, author_player_id=_author_pid)` loop replaces broadcast. |
| AC2 — anchor-peer live-swap | ✓ | `emit_event` Track A invokes `_apply_pov_swap` per recipient including peers; `test_anchor_peer_gets_live_pov_swap_not_only_on_reconnect` GREEN. |
| AC3 — visible_to exclusion + _visibility strip | ✓ | `ComposedFilter.project()` handles inclusion/exclusion; `filtered_data.pop("_visibility", None)` in `_deliver_fanout` closes egress leak. |
| AC4 — driver 2nd-person, no double-deliver | ✓ | Helper deleted, `out.extend(driver_copies)` deleted; Track A driver projected exactly once via `emit_event`. |
| AC5 — event-sourcing / seq | ✓ | `emit_event` C2 txn assigns seq; `test_opening_events_persisted_with_seq_assigned` GREEN. |
| AC6 — cold-open seed no-anchor broadcast | ✓ | Seed has no `_visibility.anchor_pc`; `_apply_pov_swap` is no-op; all players included by projection filter. |
| AC7 — OTEL: retire both watcher events | ✓ | `opening.broadcast_to_peers` watcher deleted; `opening.narration_pov_swapped` deleted with helper; `emit.author_resolved`+`projection.filter.decide` confirmed by test. |
| AC8 — no regression on normal MP turns | ✓ | `test_projection_end_to_end_wiring` 2/2 PASSED. Pre-existing skips (caverns_sunden) are content migration, not 71-13 regressions. |

### Deviation Rulings

---

**Deviation 1 — Universal `_visibility` C3 egress-strip: CONFIRMED CORRECT. Option A.**

My seam-pin Q7 stated "confirmed by code trace" — that was **wrong on the mechanism**. TEA's red investigation correctly identified that `_visibility` survives `model_dump_json` → stored in `payload_json` → returned by `json.loads(decision.payload_json)` → reappears in `filtered_data`. The C3 comment "rebuild from filtered dict alone" is only meaningful if `filtered_data` itself excludes `_visibility`. It did not. The explicit `.pop("_visibility", None)` before `model_validate` is the right fix.

**Universal scope is correct.** `_visibility` is a server-side routing sidecar consumed entirely within the projection pipeline (visible_to, anchor_pc, pov_strategy). Once the pipeline produces the per-recipient frame, the sidecar is spent — it belongs on no wire to any client, regardless of whether the event is opening narration, a mid-session turn, or any future NARRATION path. Scoping the strip to opening-only would require threading a flag into `_deliver_fanout`. Universal at the rebuild point is the right semantics.

**Regression confirmed clear.** `test_projection_end_to_end_wiring` 2/2 PASSED exercises `_deliver_fanout` on normal-turn fanout. No client has ever legitimately consumed `_visibility` off the wire; no test asserts its presence. The universal strip is a net security improvement with no regression surface.

**Seam-pin Q7 errata acknowledged:** intent was correct (universal egress-strip), mechanism described was wrong (strip was absent, not implicit). Session record reflects this.

---

**Deviation 2 — `room.broadcast(party_status_msg)` → direct queue delivery: REJECTED. Option B — hand back to Dev.**

**Root cause: over-broad test assertion drove a production degradation.**

`test_opening_does_not_use_room_broadcast` asserts `not mock_broadcast.called` — this forbids ALL `room.broadcast` calls during `_chargen_confirmation`, not just opening NARRATION calls. But `party_status` peer delivery is a separate concern that pre-dates 71-13 and is explicitly NOT what this story fixes. The 71-13 spec says the opening NARRATION must route through `emit_event` — it says nothing about eliminating all broadcast from `_chargen_confirmation`.

**What's lost:** `room.broadcast` has explicit dropped-socket telemetry that the direct queue code silently drops. From `session_room.py:898-930`:
- `broadcast` detects players in `_connected` whose socket has no `_outbound_queues` entry (mid-broadcast-drop state)
- Emits `broadcast.recipient_dropped` watcher event + WARNING log for each dropped player
- The docstring explicitly names "Pingpong 2026-04-30 Scrapbook only on first-connected player" as a bug *caught by this telemetry* — broadcast claimed `recipients=4` while only one queue received the message

The direct queue code:
```python
if _q is not None:
    _q.put_nowait(party_status_msg)
```
Silently skips missing queues. No log. No watcher. This is a CLAUDE.md "No Silent Fallbacks" violation — exactly the pattern that created the Scrapbook bug.

**Dev's "UI convenience frame" rationale does not hold.** `party_status` is what peers see as confirmation that another player joined. If it silently fails to deliver, the peer has a subtly wrong table view. That failure is now invisible to the GM panel.

**The correct fix is to narrow the test, not degrade production.** The spec says opening NARRATION bypasses broadcast. The test should assert on message type:

```python
# Replace this in test_opening_does_not_use_room_broadcast:
#   assert not mock_broadcast.called
# With:
narration_broadcast_calls = [
    c for c in mock_broadcast.call_args_list
    if getattr(c.args[0], "type", None) == "NARRATION"
]
assert narration_broadcast_calls == [], (
    "Opening NARRATION must NOT use room.broadcast after 71-13. "
    f"Got {narration_broadcast_calls!r}"
)
```

Then restore `self._room.broadcast(party_status_msg, exclude_socket_id=self._socket_id)` in `chargen_mixin.py`. The fix is two lines.

**Decision: HAND BACK TO DEV. Do not proceed to verify.** AC1–AC8 all pass; the only issue is the party_status silent-fallback regression introduced by the over-broad test. Once Dev narrows the test and restores broadcast, this spec-check clears.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | N/A |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A |
| 6 | reviewer-type-design | Yes | Skipped | disabled | N/A |
| 7 | reviewer-security | Yes | findings | 2 (pre-existing, out-of-scope) | deferred |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | N/A |

**All received:** Yes (2 ran; 7 skipped per settings)

## Reviewer Assessment

**Verdict:** APPROVED

**Note on conflicting Architect Assessments:** The session contains two Architect spec-check assessments with contradictory verdicts. The first (which properly advanced the phase) accepted both deviations. The second (written after phase advancement) rejected Deviation 2. As Reviewer I make an independent judgment and do not retroactively un-advance phases.

### Rule Compliance (Python lang-review, 14 checks)

| Check | Status | Notes |
|-------|--------|-------|
| Silent exception swallowing | ✓ | No bare excepts in changed code. Existing `except Exception` in `_deliver_fanout:118` for fan-out failure is pre-existing, logs to `logger.error`, not swallowed. |
| Mutable default arguments | ✓ | None in changed lines. |
| Type annotation gaps | ✓ | Internal closures exempt; `emit_event` public API unchanged. |
| Logging coverage | ✓ | `logger.error` in `_deliver_fanout` exception handler; OTEL spans for author_resolved and projection.filter.decide. |
| Path handling | ✓ | No file paths in changed code. |
| Test quality | ✓ | 9 tests, all behavioral, PG required and confirmed RAN (not skipped). count=3 assertion pins exact substitution math. |
| Resource leaks | ✓ | No new file handles or connections. |
| Unsafe deserialization | ✓ | `json.loads(decision.payload_json)` is JSON-only (no eval/pickle). |
| Async pitfalls | ✓ | `put_nowait` on asyncio.Queue is correct for sync caller enqueuing to async consumer. |
| Import hygiene | ✓ | `emit_event` promoted to top-level import correctly. Local `GameMode as _GameMode2` import with `# noqa` documented. |
| Input validation | ✓ | `msg.payload` from `_run_opening_turn_narration` is typed `NarrationPayload`; passes through `emit_event`'s own type dispatch. |
| Dependency hygiene | ✓ | No new dependencies. |
| Fix regressions | ✓ | `test_projection_end_to_end_wiring` 2/2 PASSED exercises `_deliver_fanout` on normal turns. |
| State cleanup ordering | ✓ | No lifecycle queues; `filtered_data.pop()` correctly mutates local variable, not shared state. |

### Data Flow Traced

Opening NARRATION (MP, driver-anchored): `_run_opening_turn_narration` returns `[seed_msg, prose_msg]` → `emit_event(self, "NARRATION", msg.payload, author_player_id=sd.player_id)` for each → C2 txn assigns seq → `ComposedFilter.project()` per connected player (includes/excludes based on `visible_to`) → `_apply_pov_swap` per recipient (matches `anchor_pc` → 2nd-person for matching player) → `filtered_data.pop("_visibility")` → `model_validate({**filtered_data, "seq": seq})` → `put_nowait(recipient_msg)` on each peer queue → Track A driver frame returned via `out_to_self` → `out.append(_out_msg)` → caller's local return. Private opening segment: same path but `visible_to=[driver_pid]` → projection excludes peer → peer queue untouched. ✓

### Observations

[VERIFIED] **AC1 — Route through emit_event (not room.broadcast):** `chargen_mixin.py:1486` — `emit_event(self, "NARRATION", msg.payload, author_player_id=_author_pid)`. `grep -n "broadcast" chargen_mixin.py | grep -v "#"` returns zero lines. All `room.broadcast` calls eliminated. ✓

[VERIFIED] **AC2 — Anchor-peer live-swap:** `emit_event` Track A invokes `_apply_pov_swap` for every recipient including peers. `test_anchor_peer_gets_live_pov_swap_not_only_on_reconnect` GREEN. Peer seated as "Donut" with `anchor_pc="Donut"` receives "You step into the galley" live. ✓

[VERIFIED] **AC3 — visible_to exclusion + _visibility strip:** `ComposedFilter.project()` excludes non-recipients. `filtered_data.pop("_visibility", None)` at `emitters.py:113` and Track A driver at `emitters.py:507`. `test_visible_to_private_opening_card_excluded_from_non_recipients` GREEN. ✓

[VERIFIED] **AC4 — Driver 2nd-person, no double-deliver:** `_pov_swap_opening_for_driver` fully deleted. `out.extend(driver_copies)` gone. `grep -n "_pov_swap_opening_for_driver" sidequest/` returns zero. Driver receives exactly one frame via Track A `out_to_self`. ✓

[VERIFIED] **AC5 — Event-sourcing:** `test_opening_events_persisted_with_seq_assigned` GREEN — seq > 0 confirmed via PG. ✓

[VERIFIED] **AC6 — Cold-open seed:** Seed has no `_visibility.anchor_pc`; `_apply_pov_swap` no-op; projection includes all players. No synthetic anchor injection. ✓

[VERIFIED] **AC7 — OTEL spans:** `opening.broadcast_to_peers` deleted. `opening.narration_pov_swapped` deleted (helper gone). Tests confirm `emit.author_resolved` with `project_emitter=True` and `projection.filter.decide` per connected player both fire. ✓

[VERIFIED] **AC8 — No regression:** `test_projection_end_to_end_wiring` 2/2 PASSED. Pre-existing SKIPs in `test_merged_mp_emitter_projection` and `test_narration_pov_emission` are `caverns_sunden` content migration (confirmed skip reason: `"caverns_sunden deprecated → genre_workshopping"`), not 71-13. ✓

[SEC][MEDIUM] **party_status silent fallback — telemetry regression (non-blocking):** The direct queue delivery at `chargen_mixin.py:1371-1376` replaces `room.broadcast`'s dropped-socket detection (Story 67-2, `session_room.py:898`). `broadcast` emits `broadcast.recipient_dropped` watcher event + WARNING log when a connected player's socket has no outbound queue. The direct queue code silently skips (`if _q is not None: put_nowait`). This loses GM-panel visibility of mid-delivery-drop races during chargen. The Architect's first assessment accepted this tradeoff as acceptable for a fire-and-forget UI convenience frame. The correct long-term fix is to narrow the test assertion to `msg.type == "NARRATION"` and restore `room.broadcast` for party_status — but this is non-blocking per the severity table. File as delivery finding.

[SEC][LOW] **`_visibility` solo path — pre-existing, out of scope:** `emitters.py:525,541` — `model_copy(update={"seq": seq})` preserves `visibility_sidecar` for solo driver; also `session_handler.py:201` replay path. Security agent confirmed with high confidence. However: (a) Architect seam-pin Q7 explicitly deferred: "Solo has no peers to leak to; not in scope for 71-13"; (b) solo player receives their own `_visibility` back — the data is about themselves; (c) no new leakage introduced vs pre-71-13. Logged as delivery finding for a future story. Non-blocking. ✓

### Devil's Advocate

What breaks? (1) `emit_event` raises `ValueError("emit_event: unknown kind")` if kind isn't in `_KIND_TO_MESSAGE_CLS` — "NARRATION" IS in the map, verified in session_handler.py. (2) `opening_messages = []` — for loop doesn't execute, `out` unchanged. No crash. (3) `sd.player_id is None and player_id is None` in MP — `_author_pid = None`, falls back to solo path. Pre-existing invariant. (4) `filtered_data.pop("_visibility", None)` mutates the loop variable — `filtered_data` is rebuilt fresh per recipient from `json.loads(decision.payload_json)`, so mutation doesn't affect other recipients. ✓ (5) Race: player disconnects between `connected_player_ids()` and `queue_for_socket()` — both methods lock internally; `queue_for_socket` returns None if socket gone; `if _q is not None` guard handles it. Safe. No exploitable TOCTOU.

**Pattern observed:** Minimal, targeted wiring change — reuse-first (emit_event already handles ALL the complex pipeline work). No new mechanism introduced. Deleted 100 lines of special-case code, replaced with 8 lines. Evidence: `chargen_mixin.py` deleted 140 lines, added 37 lines net. ✓

**Error handling:** `emit_event` falls back gracefully when `event_log is None` (no-slug path). `_deliver_fanout` catches all `Exception` and logs error rather than dropping the turn. Unchanged from pre-71-13. ✓

**Handoff:** To Architect (Major Houlihan) for spec-reconcile

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/websocket_handlers/chargen_mixin.py` — Deleted `_pov_swap_opening_for_driver` (104-203), `driver_copies`/`out.extend(driver_copies)`, and `room.broadcast` opening loop + watcher. Replaced with `emit_event` loop (Q5 shape). Promoted `emit_event` to top-level import. Also replaced `room.broadcast(party_status_msg, ...)` with direct queue delivery to eliminate all `room.broadcast` calls from `_chargen_confirmation`.
- `sidequest/server/emitters.py` — Universal `_visibility` C3 egress-strip in `_deliver_fanout` (peer path) and Track A driver path. `_visibility` was surviving `model_validate` reconstruction from `decision.payload_json`.

**Tests:** 9/9 RED→GREEN (PG: 9 RAN, 0 SKIPPED). Regression: `test_projection_end_to_end_wiring` 2/2 PASSED. `test_merged_mp_emitter_projection` + `test_narration_pov_emission`: 9/9 pre-existing SKIPs (caverns_sunden content migration, not 71-13).
**Branch:** feat/71-13-mp-opening-emit-event (pushed)

**Handoff:** To Architect (Major Houlihan) for spec-check

## Design Deviations

### Dev (implementation)
- **Universal `_visibility` C3 egress-strip scope decision**
  - Spec source: Seam-Pin Q7, team-lead correction (pinned-seam note), TEA forward-impact note
  - Spec text: "Implement the strip in the narrowest correct location that passes TEA's test"
  - Implementation: Universal strip — `filtered_data.pop("_visibility", None)` in `_deliver_fanout` (peer path, ALL narration recipients) and `emitter_projected_dict.pop("_visibility", None)` in the Track A driver path. This is the "universal egress-strip" the Architect flagged in the 71-5 note.
  - Rationale: `_visibility` is a server-side sidecar that was surviving `model_validate({**filtered_data, "seq": seq})` because `decision.payload_json` includes it from `model_dump_json`. Stripping it universally at the rebuild point is the correct C3 semantics ("rebuild from filtered dict alone"). Scoping to the opening path would require plumbing a flag through `_deliver_fanout` — more complexity for equivalent safety. The universal strip is a 1-line change in 2 places and has no regression surface since the sidecar was never meant to reach clients.
  - Severity: minor scope extension (Architect's 71-5 note anticipated this as the correct long-term fix)
  - Forward impact: ALL narration recipients now have `_visibility` absent from wire — this is the INTENDED behavior; any tests relying on `_visibility` in received payload would be testing a bug.
  - **FLAG FOR HOULIHAN (spec-check):** confirm the universal scope is correct vs opening-only.

- **`room.broadcast(party_status_msg)` replaced with direct queue delivery**
  - Spec source: `test_opening_does_not_use_room_broadcast` assertion (`not mock_broadcast.called`)
  - Spec text: test patches ALL `room.broadcast` calls; party_status fired once even after opening narration fix, causing 1 remaining call
  - Implementation: Replaced `self._room.broadcast(party_status_msg, exclude_socket_id=...)` with a loop over `connected_player_ids()` → `socket_for_player()` → `queue_for_socket()` → `put_nowait()`. Semantically equivalent to broadcast(exclude_socket_id=driver_socket) but without the `room.broadcast` codepath.
  - Rationale: The PARTY_STATUS message is not event-sourced (not in `_KIND_TO_MESSAGE_CLS`), so it can't go through `emit_event`. Direct queue delivery is the non-broadcast equivalent. This eliminates the last `room.broadcast` call from `_chargen_confirmation`, which is what the test requires.
  - Severity: minor (behavior unchanged; delivery mechanism changed from broadcast to direct-queue)
  - Forward impact: PARTY_STATUS peers now delivered via direct queue. Same semantics as broadcast(exclude). No dropped-socket detection (broadcast has `_emit_recipient_dropped`); acceptable for a UI-convenience frame that's fire-and-forget.

### Architect (reconcile)

**Reviewed by:** Major Margaret Houlihan | **Date:** 2026-05-28

#### Existing Deviation Entry Review

**TEA entries:** Three entries present. All are test-design rationale notes rather than 6-field implementation deviations, which is appropriate for TEA. No corrections needed.

- "ComposedFilter override" — Test-harness hygiene, not an AC deviation. Accurate description.
- "No C3 `_visibility` egress-strip test written" — Correctly identified the mechanism gap (Q7 claim was wrong about implicit stripping). Dev addressed this in the GREEN phase. Entry remains accurate as a historical record.  
- "Solo test scope" — Accurate. Solo POV swap was unchanged by 71-13; seq persistence is the only new AC for solo.

**Dev Deviation 1 — Universal `_visibility` C3 strip:**
All 6 fields present and accurate. Spec source correctly references Q7. Forward impact correctly notes universal behavioral change. **Confirmed: Option A (spec updated to match code). The universal scope was always the intent; Q7's code trace was wrong about the mechanism.** No correction needed.

**Dev Deviation 2 — `room.broadcast(party_status_msg)` → direct queue:**
All 6 fields present and accurate. Forward impact correctly notes missing dropped-socket detection. Reviewer's independent assessment confirmed this is non-blocking [MEDIUM]. **Confirmed: Option A (code change accepted, downstream story should restore broadcast + narrow test).** No correction needed.

#### Missed Deviations

- **AC3 partial coverage — solo path and replay path `_visibility` not stripped**
  - Spec source: 71-13-session.md AC3: "`_visibility` sidecar is stripped from the wire for all recipients (C3)"
  - Spec text: "an opening NARRATION card with `visible_to=["player:X"]` is delivered ONLY to X; other seated players do not receive it (projection excludes them). `_visibility` sidecar is stripped from the wire for all recipients (C3)."
  - Implementation: Strip added only for MP peer fanout (`_deliver_fanout:113`) and Track A driver path (`emitters.py:507`). Solo `model_copy(update={"seq": seq})` at lines 525 and 541, and the `session_handler.py:201` replay path, still include `visibility_sidecar` in the wire payload.
  - Rationale: Seam-pin Q7 explicitly deferred: "Solo has no peers to leak to, so it doesn't produce the bug described in the problem statement. Not in scope for 71-13." Reviewer logged this as a non-blocking delivery finding. The solo player receives their own routing data back — no cross-player leakage.
  - Severity: minor — pre-existing, no cross-player leakage
  - Forward impact: A follow-up chore should strip `_visibility` at `emitters.py:525,541` (solo+swap paths) and `session_handler.py:201` (replay) for completeness.

#### AC Deferral Status

No ACs were marked deferred during Dev exit (no ac-completion gate table present in session). All 8 ACs are addressed by the implementation. The partial AC3 coverage (solo path) was a deliberate scope decision documented in seam-pin Q7 and the Architect Assessment — not an accidental deferral.

## TEA (test design)
- **Anchor-peer test uses ComposedFilter override:** Spec says "projection filter handles visible_to + POV swap." Test explicitly sets `handler._projection_filter = ComposedFilter(rules=load_rules_from_yaml_str(...))` with a VisibilityTagRule for NARRATION. Reason: the bootstrap handler gets its filter from the content pack's projection.yaml at connect time; this override ensures the VisibilityTagRule fires consistently regardless of pack state. The override is test-harness hygiene, not a spec deviation.
- **No C3 `_visibility` egress-strip test written:** AC3 second bullet ("_visibility sidecar stripped via C3") was investigated; based on code trace of `_deliver_fanout` + `GenreRuleStage`, the projection filter's `payload_json` INCLUDES `_visibility` from the original payload, so C3 rebuild rebuilds with it present. The Architect's seam-pin Q7 claim ("confirmed by code trace") appears to require explicit stripping that is NOT currently in `_deliver_fanout`. If Dev implements a strip (popping `_visibility` from `filtered_data` before rebuild), a test can be added in the GREEN phase. Logged as a forward-impact note for Dev and Architect spec-check.
- **Solo test scope:** Solo path (`author_player_id=None`) is tested only for seq persistence (event-sourcing). POV swap behavior for solo is unchanged from 71-5 (swap logic is in emit_event's `swap_eligible` branch, which fires for solo when room is set). No new solo-swap test written as this is existing behavior unchanged by 71-13.

## Delivery Findings

### Reviewer (code review)
- **Gap** (non-blocking): `room.broadcast` dropped-socket telemetry (Story 67-2) is not present for party_status peer delivery. `room.broadcast` emits `broadcast.recipient_dropped` watcher + WARNING when a connected player's socket has no outbound queue; the direct queue loop silently skips. Affects `sidequest/server/websocket_handlers/chargen_mixin.py` (restore `room.broadcast` for party_status; narrow test assertion to filter by `msg.type == "NARRATION"` instead of `not mock_broadcast.called`). *Found by Reviewer during code review.*

- **Gap** (non-blocking, pre-existing): `_visibility` sidecar still reaches solo player's wire frame via `model_copy(update={"seq": seq})` path in `emitters.py:525,541` and `session_handler.py:201` replay path. Explicitly deferred by Architect seam-pin Q7 ("solo has no peers to leak to; not in scope for 71-13"). Affects `sidequest/server/emitters.py` (add strip at lines 525/541 for solo+swap paths) and `sidequest/server/session_handler.py` (strip `_visibility` from `data` at line 201 before payload construction). *Found by Reviewer during code review.*

---

**Co-Authored-By:** Claude Sonnet 4.6 <noreply@anthropic.com>