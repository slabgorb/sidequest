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
   - Integration test: Multiplayer opening narration with 2+ PCs, verify both the driving player and peers receive swapped cards with "You..." instead of name.
   - End-to-end: Manual playtest — open a 2-player MP session, confirm the opening narration on both tabs reads "You..." from each player's perspective.

## Workflow Tracking

**Workflow:** tdd
**Phase:** research/development
**Phase Started:** 2026-05-27

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| research | 2026-05-27 | - | - |

## Delivery Findings

- The `_apply_pov_swap()` function exists in `emitters.py` and is already called for peers during perception fanout in `emit_event()`.
- The opening narration is broadcast via `room.broadcast()` without going through `emit_event()`, so the POV-swap layer is never invoked for the driving player.
- The visibility sidecar (_visibility) is already embedded in the narration payload by the narrator (per ADR-036 / story 49-8), so we have the anchor_pc and pov_strategy needed to apply the swap.
- The `_pronouns_for_pc()` helper is already available in `emitters.py` to retrieve pronouns from snapshot.
- The integration point is in `chargen_mixin.py`, where opening_messages are created and broadcast, before they're returned to the handler's local caller.

## Design Deviations

None yet.
