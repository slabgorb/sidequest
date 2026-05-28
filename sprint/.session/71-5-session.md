---
story_id: "71-5"
jira_key: none
epic: "71"
workflow: "tdd"
---

# Story 71-5: MP opening narration — POV-swap the driving player's own card (not raw-bypass)

## Story Details
- **ID:** 71-5
- **Jira Key:** None (sidequest-server is personal repo)
- **Workflow:** tdd
- **Type:** Bug fix
- **Points:** 3
- **Epic:** 71 (MP turn coordination & multiplayer opening narration)
- **Stack Parent:** None

## Problem

In multiplayer, the opening narration is generated/driven by one player (the "driving player" — whoever commits chargen last with >1 PC seated), then broadcast to all players. The bug: the driving player's own card currently uses a "raw-bypass" (the unswapped narration) instead of being POV-swapped to second person like other players receive.

**Expected behavior:** The driving player's own card should read "You step into the galley and..." (second-person POV, swapped to their character's perspective).

**Actual behavior:** The driving player's own card reads "Carl steps into the galley and..." (third-person, raw, unswapped).

**Why it matters:** The driving player is still a player at the table, not an observer. They should see their own actions in second person, consistent with how the narrator treats their non-opening actions and consistent with how peers see the opening (already POV-swapped per ADR-036, story 49-8).

## Technical Analysis

### Code Path

The opening narration flow in multiplayer:

1. **First committer (solo seats, party incomplete):** Chargen fires, `_should_fire_opening_narration()` defers because player count < min_players. `opening_seed` + `opening_directive` are stashed but NOT consumed.

2. **Last committer (all seats filled):** Chargen fires, `_should_fire_opening_narration()` returns True. `_run_opening_turn_narration()` is called:
   - Consumes `opening_seed` → cold-open NARRATION message
   - Consumes `opening_directive` → narrator's Early zone
   - Calls narrator
   - Returns `messages = cold_open_messages + narrator_messages`

3. **Broadcast to peers:**
   ```python
   if (self._room is not None and sd.mode == GameMode.MULTIPLAYER 
       and self._socket_id is not None and opening_messages):
       for _msg in opening_messages:
           self._room.broadcast(_msg, exclude_socket_id=self._socket_id)
   ```
   - **Bug:** Messages broadcast via `room.broadcast()` (raw, unfiltered)
   - **Missing:** The driving player (`self._socket_id`) receives the messages in the handler's local return, but those messages are **NOT POV-swapped**
   - The broadcast to peers gets perception-filtered + POV-swapped by the projection layer (implicit — peers reconstruct from event log on reconnect), but the driving player's local return is the raw output from the narrator

4. **Why the bypass happens:**
   - The narrator generates narration from the perspective it was prompted with (via `opening_directive`)
   - For MP opening, the narrator prompts "narrate the opening from each PC's point of view"
   - The opening narration is broadcast-shared ("visible_to":"all" in the visibility sidecar)
   - Each peer gets their own POV-swapped copy (the sidecar anchors to their PC name, and `_apply_pov_swap()` fires per-recipient)
   - **The driving player's local return bypasses the projection layer entirely** — it's returned directly from the narration method without going through `emit_event()`'s perception filter or POV-swap logic

### Where POV-Swap Should Fire

The fix is in `chargen_mixin.py`, where the opening messages are constructed and broadcast. The messages should be POV-swapped for the driving player before being returned to the handler's caller (who puts them on the socket).

The opening narration has a `_visibility` sidecar in the payload (set by the narrator) with:
- `anchor_pc`: the character name driving the narration
- `pov_strategy`: "pc_anchored" (from ADR-036, story 49-8)

The `_apply_pov_swap()` function in `emitters.py` already knows how to swap:
1. Check if recipient is the anchor PC
2. If yes, get their pronouns from the snapshot
3. Call `swap_to_second_person(text, target_name=anchor_pc, pronouns=pronouns)`
4. Return the swapped prose

### OTEL Observability

Per CLAUDE.md, every backend fix touching narration/POV must emit OTEL watcher events so the GM panel can verify the swap fired. The existing code emits:
- `narration.second_person_swap` (span in `pov_swap.py`) — documents swap_count
- We should add a watcher event for opening-specific POV swap: `opening.narration_pov_swapped` with the driving player ID, anchor PC, swap count, and original text length

## Acceptance Criteria

1. **Functional:** The driving player's opening narration card (both cold-open seed and narrator prose) is POV-swapped to second person when the anchor_pc matches their character name.
2. **Consistent:** The swap behavior is identical to how peer players receive their swapped cards — same `_apply_pov_swap()` logic, same visibility sidecar contract.
3. **Observed:** A watcher event `opening.narration_pov_swapped` is emitted for the driving player's opening narration, with attributes: `driver_player_id`, `anchor_pc`, `anchor_pronouns`, `swap_count`, `original_text_length`, `swapped_text_length`.
4. **Tested:** 
   - Unit test: POV-swap fires on a cold-open NARRATION message when anchor_pc and driver PC match.
   - Unit test: POV-swap is correctly skipped (no-op) when anchor_pc ≠ driver PC.
   - Integration test: Multiplayer opening narration with 2+ PCs (single shared blob anchored to the driver's PC). Verify the DRIVING player's own card is swapped to "You..." AND peers receive the card in THIRD person ("<anchor_pc name> steps...") — peers are non-anchor, so third person is CORRECT, not a regression. Assert peers' received bytes are byte-identical to today.
   - End-to-end: Manual playtest — open a 2-player MP session, confirm the opening narration reads "You..." on the DRIVING player's tab and "<driver PC name>..." (third person) on the peer's tab.

**Scope note (Architect ruling 2026-05-28):** The MP opening is a SINGLE shared blob anchored to ONE PC (the lead/driver PC), per `classify_narration_visibility` + ADR-105 B3. Therefore peers seeing third person is the CORRECT rendering for a single-anchor blob (they are non-anchor; `_apply_pov_swap` no-ops for them by design). The bug is genuinely DRIVER-ONLY. A *personal* 2nd-person opening for every player would require per-PC opening generation — that is a NEW FEATURE, explicitly OUT OF SCOPE for 71-5, file separately if the product wants it. Earlier "Finding 1" (peers' live broadcast is raw) is NOT a defect under this architecture.

## Workflow Tracking

**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-05-28T03:22:37Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| research | 2026-05-27 | - | - |

## Sm Assessment

Setup verified for peloton handoff to TEA (Radar O'Reilly) for the RED phase. Server-side MP narration bug: the driving player's own opening card is raw-bypassed (third-person "Carl steps...") instead of POV-swapped to second person ("You step...") like peers already get. Root cause is clean and identified: opening narration broadcasts via `room.broadcast()` directly, skipping the `emit_event()` perception-fanout layer where `_apply_pov_swap()` runs. The swap helper, the pronoun helper, and the visibility sidecar (anchor_pc + pov_strategy, per ADR-036/49-8) all already exist — this is a wiring/integration fix at the chargen_mixin opening-broadcast point, not new machinery.

**Routing notes for the team:**
- TEA leads RED. Three AC scenarios: swap fires for the driving player's own card; swap correctly skipped where it should be (verify the existing peer behavior isn't regressed); MP integration end-to-end.
- ⚠️ OTEL REQUIRED (project doctrine — this is a backend subsystem fix): add a watcher event `opening.narration_pov_swapped` (driver_player_id, anchor_pc, swap_count, pre/post text lengths) so the GM panel can verify the swap actually fired and the narrator isn't just improvising. The GM panel is the lie detector — without the OTEL emit, we can't tell the swap engaged. TEA: include a test asserting the OTEL event fires; Dev: wire the emit. This is a Keith/dev observability concern, NOT a player-facing surface — frame it as engine verification.
- Reuse-first: Dev must reuse `_apply_pov_swap()` + `_pronouns_for_pc()` from emitters.py — do NOT reimplement POV logic. The fix routes the driving player's opening card through the existing swap path.
- Perception note for Reviewer: applying the swap to the driving player's own card must NOT alter what PEERS receive (they're already correctly swapped per 49-8) — confirm no regression to the peer fanout, and that the visibility sidecar is consumed, not leaked into the rendered card.
- Architect on standby — ADR-036/067 narration-path implications; worth a spec-check at green that the integration point (chargen_mixin broadcast vs emit_event) is the right seam and doesn't double-swap.

Branch `feat/71-5-mp-opening-narration-pov-swap` off sidequest-server develop (05a9a6c, includes 71-1's #482). No Jira. Clear to hand to TEA.

## Delivery Findings

- The `_apply_pov_swap()` function exists in `emitters.py` and is already called for peers during perception fanout in `emit_event()`.
- The opening narration is broadcast via `room.broadcast()` without going through `emit_event()`, so the POV-swap layer is never invoked for the driving player.
- The visibility sidecar (_visibility) is already embedded in the narration payload by the narrator (per ADR-036 / story 49-8), so we have the anchor_pc and pov_strategy needed to apply the swap.
- The `_pronouns_for_pc()` helper is already available in `emitters.py` to retrieve pronouns from snapshot.
- The integration point is in `chargen_mixin.py`, where opening_messages are created and broadcast, before they're returned to the handler's local caller.

### TEA (test design)
- **Finding 1 — Gap** (non-blocking, scope check): `room.broadcast()` (session_room.py:865) does NOT POV-swap — it `put_nowait`s the raw message onto every peer queue. So in a LIVE MP session peers receive the raw 3rd-person opening; the swap for peers only happens via event-log projection on RECONNECT (lazy_fill). For single-anchor this is CORRECT (peers are non-anchor → 3rd-person is right). Logged so it's tracked: if a future story wants per-PC openings, the peer live-broadcast path would need routing through `emit_event`. *Found by TEA during test design.*
- **Finding 2 — Gap** (blocking for AC1 seed): the cold-open seed NARRATION is built as a bare `NarrationPayload(text=...)` with NO `_visibility` sidecar (websocket_session_handler.py:2476). `_apply_pov_swap` no-ops without `anchor_pc`/`pov_strategy`. AC1 wants the SEED swapped too — so Dev must stamp the driver anchor onto the cold-open seed (or the seed won't swap). My test's canned seed carries the sidecar to assert the intended behavior; Dev must make production stamp it. *Found by TEA during test design.*
- **Finding 3 — Question** (non-blocking): I recommended a thin `_pov_swap_opening_for_driver(messages, *, driver_player_id, view, snapshot)` helper as the testable seam; team-lead directed the integration harness instead. The test now drives `_chargen_confirmation` end-to-end. If Dev extracts such a helper anyway, a faster unit test could supplement. *Found by TEA during test design.*

## Design Deviations

### TEA (test design)
- **Opening narration mocked; opening fire forced; MP room rebuilt (not a 2-committer walk)**
  - Spec source: AC4 "MP integration with 2+ PCs"
  - Spec text: "Multiplayer opening narration with 2+ PCs, verify both the driving player and peers receive [correct] cards"
  - Implementation: the integration test reuses the bootstrap solo chargen walk to build the driver (Rux), rebinds the handler onto a fresh MULTIPLAYER SessionRoom (driver + seated peer Donut), monkeypatches `_should_fire_opening_narration`→True and `_run_opening_turn_narration`→a canned anchored opening, and drives the real `_chargen_confirmation`. It does not run two real committers through the full MP chargen barrier.
  - Rationale: `_chargen_confirmation` has no isolatable seam; a full two-committer MP chargen walk is a large, brittle harness. The canned anchored opening + forced fire exercise the actual opening-broadcast block (driver local `out` swap + peer `room.broadcast`) — the fix's true locus — through the real method.
  - Severity: minor
  - Forward impact: Reviewer should confirm the real `_run_opening_turn_narration` emits a single driver-anchored `_visibility` sidecar in MP (the test assumes this shape), and that the cold-open seed is stamped (Finding 2).
- **Requires Postgres**: the connect path persists to PG (ADR-115); the test needs `SIDEQUEST_TEST_DATABASE_URL` and skips cleanly when unset. Environment note, not a spec deviation.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED — 3 failing (ready for Dev), 2 guards passing. Lint clean.
**Test file:** `tests/server/test_opening_pov_swap_71_5.py` (commit 3916765)
**Run:** `SIDEQUEST_TEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test uv run pytest -n0 tests/server/test_opening_pov_swap_71_5.py`

| Test | AC | State | RED reason |
|------|----|-------|-----------|
| `test_driver_own_opening_card_is_pov_swapped` | AC1 | FAIL | driver's `out` is raw "Rux steps…", not "You step…" |
| `test_opening_pov_swapped_watcher_event_emitted` | AC3 | FAIL | `opening.narration_pov_swapped` not emitted |
| `test_peers_receive_raw_third_person_no_regression` | AC4 | FAIL | driver not swapped (peer-raw bytes guarded) |
| `test_opening_swap_skipped_when_anchor_is_not_driver` | AC2 | PASS (guard) | non-anchor card unchanged — don't over-swap |
| `test_no_pov_swapped_event_for_non_anchored_opening` | AC3-neg | PASS (guard) | no event when swap_count==0 |

**Pinned to Architect ruling:** single-anchor opening; driver-only bug; seam Option (a) — swap the driver's local copy at `chargen_mixin:1453`, peer `room.broadcast` untouched. Watcher `opening.narration_pov_swapped` with `driver_player_id, anchor_pc, anchor_pronouns, swap_count, original_text_length, swapped_text_length`, emitted only when swap_count>0.

**Handoff:** To Dev for GREEN.