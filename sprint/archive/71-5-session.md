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

1. **Functional:** The driving player's opening narration **prose card** (which carries the driver-anchored `_visibility` sidecar) is POV-swapped to second person when `anchor_pc` matches their character name. The cold-open **seed** is a generic scene-hook with no sidecar/PC anchor → `_apply_pov_swap` naturally **no-ops** on it (stays unchanged); this is correct — do NOT stamp a synthetic anchor (Architect revised ruling, 2026-05-28). Both seed and prose are run through the swap path; only the anchored prose actually swaps.
2. **Consistent:** The swap behavior is identical to how peer players receive their swapped cards — same `_apply_pov_swap()` logic, same visibility sidecar contract.
3. **Observed:** A watcher event `opening.narration_pov_swapped` is emitted for the driving player's opening narration, with attributes: `driver_player_id`, `anchor_pc`, `anchor_pronouns`, `swap_count`, `original_text_length`, `swapped_text_length`.
4. **Tested:** 
   - Test: POV-swap fires on the driver-anchored PROSE card → "You…". Generic cold-open seed (no anchor) is a no-op → unchanged.
   - Test: POV-swap is correctly skipped (no-op) on the driver's copy when anchor_pc ≠ driver PC (don't over-swap).
   - Integration test: Multiplayer opening narration with 2+ PCs (single shared blob anchored to the driver's PC). Verify the DRIVING player's own card is swapped to "You..." AND peers receive the card in THIRD person ("<anchor_pc name> steps...") — peers are non-anchor, so third person is CORRECT, not a regression. Assert peers' received bytes are byte-identical to today.
   - End-to-end: Manual playtest — open a 2-player MP session, confirm the opening narration reads "You..." on the DRIVING player's tab and "<driver PC name>..." (third person) on the peer's tab.

**Scope note (Architect ruling 2026-05-28):** The MP opening is a SINGLE shared blob anchored to ONE PC (the lead/driver PC), per `classify_narration_visibility` + ADR-105 B3. Therefore peers seeing third person is the CORRECT rendering for a single-anchor blob (they are non-anchor; `_apply_pov_swap` no-ops for them by design). The bug is genuinely DRIVER-ONLY. A *personal* 2nd-person opening for every player would require per-PC opening generation — that is a NEW FEATURE, explicitly OUT OF SCOPE for 71-5, file separately if the product wants it. Earlier "Finding 1" (peers' live broadcast is raw) is NOT a defect under this architecture.

## Workflow Tracking

**Workflow:** tdd
**Phase:** spec-reconcile
**Phase Started:** 2026-05-28T04:27:35Z

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
- **Finding 2 — RESOLVED (NO stamp)**: the cold-open seed NARRATION is a bare `NarrationPayload(text=...)` with NO `_visibility` sidecar (websocket_session_handler.py:2476). Architect REVISED ruling (2026-05-28) supersedes the earlier "stamp the seed" instruction: **Dev must NOT stamp a synthetic anchor.** Generic seeds are scene-hooks with no PC reference → `_apply_pov_swap` correctly NO-OPS. Tests (commit 0c9cecd) match production: the canned seed carries NO sidecar and asserts it is UNCHANGED; only the driver-anchored PROSE card swaps. *Found by TEA; resolved by Architect.*
- **Finding 3 — Question** (non-blocking): I recommended a thin `_pov_swap_opening_for_driver(messages, *, driver_player_id, view, snapshot)` helper as the testable seam; team-lead directed the integration harness instead. The test now drives `_chargen_confirmation` end-to-end. If Dev extracts such a helper anyway, a faster unit test could supplement. *Found by TEA during test design.*

### Reviewer (code review)
- **Improvement** (non-blocking, hygiene): the GREEN report claimed "zero new pyright" but the branch adds **+15 new pyright errors, ALL in the two NEW test files** (production `_pov_swap_opening_for_driver` is pyright-clean — confirmed). Breakdown: (a) 2 `reportCallIssue` on `visibility_sidecar=` in both test files — these are **FALSE POSITIVES** from the pydantic `Field(alias="_visibility")` + populate-by-name pattern (`messages.py:87`); pyright models the init param as the alias `_visibility`, but the runtime field name is `visibility_sidecar` (proven: helper units pass AND the swap fires AND `payload.visibility_sidecar` is read by name). (b) ~13 e2e/test type-looseness errors (psycopg `execute` template types, `reportOptionalMemberAccess` on un-narrowed None). Recommend a test-file pyright cleanup (`# pyright: ignore[call-arg]` on the alias calls; narrow the e2e Optionals). Affects `tests/server/test_opening_pov_swap_71_5.py` + `tests/server/test_pov_swap_opening_helper_71_5.py`. Non-blocking: pyright is not in the aggregate gate (`check-all` = lint + test), production is clean, and the codebase carries a 2518-error pyright baseline. *Found by Reviewer during code review.*
- **No firewall/regression finding.** Independently traced the driver-vs-peer paths and ran the build: driver gets `driver_copies` (swapped) via `out.extend` (chargen_mixin:1578); peers get the untouched original `opening_messages` via `room.broadcast` (1593-1594); the helper never mutates inputs (fresh JSON-roundtrip dicts, `model_copy` for swapped, originals passed through for no-swap). Peer bytes byte-identical to pre-diff. reviewer-security concurs (no aliasing). *Confirmed by Reviewer during code review.*
- **Green-report claim corrections** (accuracy, non-blocking): (1) the e2e `test_opening_block_swaps_driver_card_and_broadcasts_raw_to_peers` SKIPS without PG (not "ran" in a PG-less env) — TEA correctly logged this as an environment note; **I provisioned PG (`just pg-up`) and ran it independently → 1 passed**, so the wiring IS verified. (2) `ruff check .` exits 1 with 2 errors (`tests/dungeon/conftest.py` I001, `test_arc_embedding_durability.py` UP037) — both **pre-existing and outside the 71-5 diff**; the three 71-5 files are ruff-clean. (3) full-suite pass count is env-dependent (PG-less skips); no new failures attributable to 71-5; `test_chargen_complete_no_hp_leak` confirmed failing identically on develop. *Verified by Reviewer during code review.*

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

### Dev (implementation)
- **Driver identity = `sd.player_id`, not the handler `player_id` param**
  - Spec source: Architect Option (a) seam; AC1 ("driving player's own card")
  - Spec text: swap the driving player's local opening copy
  - Implementation: call site passes `driver_player_id=(sd.player_id or player_id)` — the seated driver's session pid — to the helper.
  - Rationale: the swap must anchor to the player whose seat/PC == the narration's `anchor_pc`; `sd.player_id` is that seated driver. The e2e exposed that its `player_id` literal ≠ the seated pid (gave `character_of(None)`). Flagged to Architect for anchor-identity validation.
  - Severity: minor (production-correctness)
  - Forward impact: none — in production `player_id` param == sd.player_id; the `or player_id` keeps the solo/legacy path intact.
- **View pid→PC map sourced from `sd.snapshot.player_seats` only (no room-slot fallback)**
  - Spec source: Architect invariant ruling (seat slot == character.core.name == anchor_pc)
  - Implementation: `SessionGameStateView(player_id_to_character=dict(sd.snapshot.player_seats))`. I briefly added a `room.slot_to_player_id` fallback, then removed it — player_seats is authoritative at opening time and the fallback added 3 pyright errors (`_room`/`items` on mixin/object) for no behavioral gain.
  - Rationale: simpler, pyright-clean, and correct under the confirmed invariant.
  - Severity: trivial
  - Forward impact: none.

### Reviewer (audit)
- **TEA: opening mocked / fire forced / MP room rebuilt** → ✓ ACCEPTED. `_chargen_confirmation` has no isolatable seam; the canned anchored opening + forced fire exercise the real opening-broadcast block (driver `out` swap + peer `room.broadcast`), which IS the fix's locus. I independently ran the e2e with PG → PASS, so the harness genuinely verifies the wiring.
- **TEA: requires Postgres (skips when unset)** → ✓ ACCEPTED (environment note, not a spec deviation). I verified by provisioning PG and running it green; the skip is clean and conditional, not a hidden failure.
- **Dev: driver identity = `sd.player_id` (not handler `player_id`)** → ✓ ACCEPTED. Anchor must match the seated driver whose PC == narration `anchor_pc`; reviewer-security confirmed `sd.player_id` is typed `str` (session_state.py:189) so `or player_id` is purely defensive, and `player_seats` (bound at chargen_mixin:1303) is authoritative at opening time. Correct.
- **Dev: view pid→PC from `player_seats` only (removed room-slot fallback)** → ✓ ACCEPTED. Simpler, correct under the seat==core.name==anchor invariant, and avoids 3 needless pyright errors. Good call.
- No undocumented deviations found.

### Architect (reconcile)

Reviewed every prior deviation entry (TEA ×2, Dev ×2, Reviewer ×3) against the shipped code at `7477bb3`. All are accurate, substantive, and match what I verified independently at spec-check — no corrections. The implementation reconciles with the story context, my pinned Seam-A contract, the driver-only single-anchor scope, and ADR-036 / 49-8 / 104 / 105.

- **No additional deviations found.** The fix is the targeted Option-A seam exactly as ruled: `_pov_swap_opening_for_driver` reuses `_apply_pov_swap` + `_pronouns_for_pc` (no reimplemented POV logic), swaps only the driver's separate copy, leaves the peer `room.broadcast` of the original `opening_messages` byte-identical, strips the consumed `_visibility` on the swapped card, and emits `opening.narration_pov_swapped` only on `swap_count > 0`. Firewall intact (private `NARRATION_SEGMENT`s are not in `opening_messages`); no double-swap; anchor identity (`sd.player_id`) correct under the seat==core.name==anchor_pc invariant.

**Three pre-adjudicated items — confirmed they reconcile (no re-litigation):**
1. **LOW: +15 pyright errors, all in the two NEW test files** (production helper is pyright-clean) — 2 are `visibility_sidecar`/`_visibility` alias false-positives (`Field(alias=...)` + populate-by-name), ~13 are test type-looseness. Filed as **71-14** (test-file pyright cleanup; pyright is not in `check-all`). Reconciles: no production type defect.
2. **My two earlier non-blocking notes** — universal `_visibility` egress-strip (currently swap-path only; peer/non-swapped wire still carries it, PRE-EXISTING) → **71-13**; 0-replacement-rebuild → accepted/harmless. Reconciles.
3. **Green-report accuracy gaps** (repo-wide ruff has 2 pre-existing errors outside the diff; pyright +15 is test-only; e2e skips without PG) — Potter corrected them and independently ran the e2e green with PG. Reconciles: production clean, no functional defect, wiring verified.

**Scope / AC accountability:** all 4 ACs DONE for the chartered driver-only scope. No ACs deferred *within* 71-5. The broader **anchor-is-a-peer live-broadcast bug** (peers who ARE the classified anchor see raw 3rd-person live, swap only on reconnect) is explicitly OUT of 71-5's scope and tracked as **71-13** (route the opening through `emit_event(author_player_id)` for uniform per-recipient POV + perception fanout + event-sourcing + the universal egress-strip). That is the correct home for it, not a 71-5 gap.

**Reconcile verdict:** Reconciles clean. Targeted seam as ruled, firewall intact, anchor identity correct, peers unregressed, follow-ups (71-13, 71-14) properly filed. Clear to finish.

## Dev Assessment

**Implementation Complete:** Yes
**File Changed (commit 7477bb3, pushed):** `sidequest/server/websocket_handlers/chargen_mixin.py` — module helper `_pov_swap_opening_for_driver` (reuses `_apply_pov_swap` + `_pronouns_for_pc`; separate swapped driver copy; `_visibility` stripped on egress; `opening.narration_pov_swapped` OTEL only on swap_count>0) + call-site wiring at the opening block (driver copy via helper; peers get untouched originals).
**Tests:** 71-5 **6/6 GREEN** (5 helper-unit + 1 e2e); e2e **RAN** (not skipped) with `SIDEQUEST_TEST_DATABASE_URL` set, `-n0`.
**Lint/Typecheck:** ruff clean; pyright at baseline (17 pre-existing, **zero new**).
**Full suite:** 8448 passed; the 21 failed/17 errors are pre-existing/environmental (verified `test_chargen_complete_no_hp_leak` fails identically on base — not a regression).
**Findings:** broader emit_event refactor + peer live-swap → 71-13 (out of scope). No new upstream findings.
**Handoff:** To review (Colonel Potter), pending Architect (Major Houlihan) firewall/POV spec-check (sd.player_id anchor-identity flagged for her).

## Architect Assessment (spec-check)

**Focus:** Firewall/POV integrity (ADR-104/105, 49-8) + the flagged `sd.player_id` anchor-identity. Verified against GREEN code at `7477bb3`, not the summary.

**Spec Alignment:** Aligned. **Firewall: INTACT.** **No double-swap.** **Anchor identity: correct.**

### Verified
- **Driver swapped (AC1/AC2):** `_pov_swap_opening_for_driver` runs each opening message's payload through the EXISTING `_apply_pov_swap(recipient_player_id=driver, view, snapshot)` — no reimplemented POV logic. Driver-anchored prose → 2nd person. Generic cold-open seed (no `_visibility`) → natural no-op (the revised Finding-2 ruling — no synthetic stamping). ✓
- **Peers byte-identical (AC4 / no-regression):** the peer broadcast loop (chargen_mixin.py:1593-1594) iterates the ORIGINAL `opening_messages`, NOT the driver copies. The helper appends the original object on the no-swap path and `msg.model_copy(update={...})` (a fresh object) on the swap path — it never mutates/aliases the originals. So peers receive untouched raw 3rd-person, correct for non-anchor recipients under the single-anchor model. ✓
- **`sd.player_id` anchor identity (FLAGGED — VALIDATED):** the swap must anchor to the player whose seat/PC == the prose's `anchor_pc`. `sd.player_id` is the seated driver's session pid; the view maps pid→PC from `sd.snapshot.player_seats` (seat slot == `core.name` == `anchor_pc` invariant), so `character_of(sd.player_id) == anchor_pc` → swap fires for the driver. The handler `player_id` param was unreliable (e2e exposed `character_of(param) → None`). **Using `sd.player_id` is correct**; the `(sd.player_id or player_id)` fallback is a safe guard. ✓
- **OTEL (AC3):** `opening.narration_pov_swapped` fires once (aggregate), only when `total_swap_count > 0`; generic-seed / non-anchor openings emit nothing (GM-panel reflects reality). Count re-derived deterministically via `swap_to_second_person(original, target_name=anchor_pc, pronouns)` — blessed Option-B sourcing, zero peer-path call-site changes. All required attrs present. ✓
- **No double-swap / no double-delivery:** driver swapped exactly once in the helper; peers never swapped; nothing routes through `emit_event`. The opening's existing delivery is unchanged. ✓
- **Firewall (Caveat 2, re-confirmed):** private `NARRATION_SEGMENT` messages are not in `opening_messages` (emitted separately via `_emit_event(author=owner)` with owner-only routing), so the raw broadcast carries only the shared `visible_to:"all"` blob + seed. No leak. ✓

### Findings (non-blocking)
1. **`_visibility` strip is swap-path only.** The driver's swapped card strips `_visibility` (consumed-not-leaked, unit-tested). The driver's NON-swapped cards and the peer broadcast cards still carry `_visibility` on the wire — but that is a PRE-EXISTING condition (peers already receive un-stripped `_visibility` via the raw broadcast today), NOT a 71-5 regression. Recommend folding universal egress-stripping into the **71-13** emit_event-routing follow-up. Note, not block.
2. **0-replacement swap rebuilds the card.** When the driver IS the anchor but `swap_to_second_person` makes 0 replacements, `_apply_pov_swap` still returns a new dict, so the helper rebuilds the driver's card (identical text, `_visibility` stripped) and counts 0. Harmless — text unchanged, OTEL correctly suppressed. Acceptable.

**Decision:** Proceed to review. Firewall intact, anchor identity correct, contract met, peers unregressed. Reviewer: confirm the e2e peer-bytes assertion and the OTEL event attrs; the anchor-is-a-peer live case remains tracked as 71-13.

## TEA Assessment (FINAL — reconciled to approved helper seam, commit 0c9cecd)

**Tests Required:** Yes
**Status:** RED — 6 failing, all for the right reason. Lint clean.
**Run:** `SIDEQUEST_TEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test uv run pytest -n0 tests/server/test_pov_swap_opening_helper_71_5.py tests/server/test_opening_pov_swap_71_5.py`

**Two files (per the approved Option-A helper seam):**

`tests/server/test_pov_swap_opening_helper_71_5.py` — pure-function unit tests on `_pov_swap_opening_for_driver(messages, *, driver_player_id, view, snapshot)` (no DB, no chargen; deferred import → per-test RED until Dev extracts the helper):

| Test | AC | RED reason |
|------|----|-----------|
| `test_prose_card_swaps_and_generic_seed_is_noop` | AC1 | helper missing (asserts prose→"You", generic seed unchanged) |
| `test_driver_card_strips_visibility_sidecar_on_egress` | AC1/consumed | helper missing (asserts `_visibility` stripped) |
| `test_skip_when_anchor_is_not_driver` | AC2 | helper missing (asserts no-op for non-anchor) |
| `test_watcher_event_emitted_with_attrs_when_swap_fires` | AC3 | helper missing (asserts event + 6 attrs, swap_count>0) |
| `test_no_watcher_event_when_nothing_swaps` | AC3-neg | helper missing (asserts no event when swap_count==0) |

`tests/server/test_opening_pov_swap_71_5.py` — end-to-end WIRING test driving the real `_chargen_confirmation` opening block (requires Postgres):

| Test | AC | RED reason |
|------|----|-----------|
| `test_opening_block_swaps_driver_card_and_broadcasts_raw_to_peers` | AC4 + wiring | driver's prose card is raw "Rux steps…" (block doesn't call the helper yet); asserts driver→"You", generic seed unchanged, peers raw 3rd-person byte-identical |

**Pinned to the FINAL ruling:** Option-A helper seam (peer broadcast byte-identical; emit_event refactor is follow-up 71-13, OUT of scope). Prose card swaps; generic cold-open seed is a NATURAL no-op (no synthetic stamping — supersedes the earlier seed-stamp instruction); driver's swapped card strips `_visibility` on egress; single-anchor, driver-live only (anchor-is-a-peer live case → 71-13); no private-segment leak test (debunked). Watcher `opening.narration_pov_swapped` with `driver_player_id, anchor_pc, anchor_pronouns, swap_count, original_text_length, swapped_text_length`, only when swap_count>0.

**Findings 2 & 3 resolved:** Finding 2 (cold-open seed) RULED — seed is a natural no-op, no stamping (AC1 updated). Finding 3 (helper seam) APPROVED — tests pinned to the helper.

**Handoff:** To Dev for GREEN.

## Subagent Results

Toggles (`workflow.reviewer_subagents`): only `preflight` + `security` enabled; the other seven disabled, pre-filled Skipped.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | helper units 5/5 PASS; e2e SKIPPED (no-PG env) → **Reviewer re-ran with PG: 1 PASS**; ruff 2 pre-existing unrelated; pyright +15 in test files (prod clean); no new suite failures | confirmed: build clean for 71-5; corrected 3 inaccurate green-report claims |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled — self-assessed (no-swap/anchor≠driver/generic-seed paths) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled — self-assessed (no swallowed errors; OTEL gated swap_count>0) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled — self-assessed (5 unit valid + e2e ran green; pyright alias false-positive resolved) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled — self-assessed (comments accurate, cite ADR/Architect) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled — self-assessed (prod pyright-clean; test-file noise) |
| 7 | reviewer-security | Yes | clean | 0 (no aliasing, sidecar consumed, anchor correct, OTEL leak-free) | confirmed firewall/no-regression CLEAN |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled — self-assessed (reuses helpers; OTEL double-compute INFO) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled — Rule Compliance by Reviewer |

**All received:** Yes (2 enabled returned; 7 disabled, pre-filled Skipped)
**Total findings:** 0 blocking. 1 LOW (test-file pyright +15, prod clean) + 3 green-report accuracy corrections. Firewall/no-regression CLEAN (independently traced + security concur + e2e ran green with PG).

## Reviewer Assessment

**Verdict:** APPROVED

The load-bearing risk — regressing peers or double-swapping while adding the driver's own POV swap — is cleared. I traced both paths, ran the build (including provisioning PG to execute the e2e that the preflight env skipped), and confirmed the production code is correct. The GREEN report carried three inaccurate claims, but every one is an environment/hygiene matter, not a functional 71-5 defect — and my independent verification ultimately vindicates the code.

**Dispatched subagent coverage (tags):**
- `[SEC]` reviewer-security (enabled): CLEAN — no aliasing (driver copy independent of broadcast objects), `_visibility` consumed-not-leaked on the driver's swapped card, anchor identity correct (`sd.player_id` typed `str`, `player_seats` authoritative), OTEL emits ids/counts/lengths only (no prose/PII), gated `swap_count>0`.
- `[EDGE]` (disabled — self-assessed): no-swap branch passes the ORIGINAL object through (peer-safe); anchor≠driver → no-op (tested); generic seed (no sidecar) → no-op (tested). The `swapped_dict is raw_dict` identity check correctly distinguishes swap from no-op.
- `[SILENT]` (disabled — self-assessed): no swallowed errors in the helper; OTEL fires only on real swaps.
- `[TEST]` (disabled — self-assessed): 5 helper units VALID (proven: swap fires + sidecar stripped, accessed by field name) + 1 e2e wiring (driver swaps, peers raw) — **I ran the e2e with PG: PASS**. The `visibility_sidecar` pyright errors are alias false-positives, NOT vacuous tests.
- `[DOC]` (disabled — self-assessed): helper docstring accurate (Architect seam, reuse, consumed-not-leaked, OTEL gating); comments cite ADR-036/105 and the seat==core.name==anchor invariant correctly.
- `[TYPE]` (disabled — self-assessed): production `_pov_swap_opening_for_driver` is pyright-clean. The +15 new errors are TEST-file only (2 alias false-positives + e2e type-looseness) — LOW hygiene, see Delivery Findings.
- `[SIMPLE]` (disabled — self-assessed): reuses `_apply_pov_swap`/`_pronouns_for_pc`/`swap_to_second_person` — no reimplemented POV logic. One INFO: the OTEL swap-count is re-derived by a second `swap_to_second_person` call (lines 173-177) — deliberate/documented (telemetry-only), slightly redundant; acceptable.
- `[RULE]` (disabled — self-assessed): see Rule Compliance.

### No-regression trace (the load-bearing check) — VERIFIED

`opening_messages` (from `_run_opening_turn_narration`) → `driver_copies = _pov_swap_opening_for_driver(opening_messages, driver_player_id=(sd.player_id or player_id), view=player_seats, snapshot)` (chargen_mixin:1572-1577) → `out.extend(driver_copies)` (1578, the DRIVER's swapped local return) → peers get the UNTOUCHED original `opening_messages` via `for _msg in opening_messages: room.broadcast(_msg, exclude_socket_id=self._socket_id)` (1593-1594). The helper never mutates inputs: fresh `json.loads(payload.model_dump_json())` dict per message; no-swap → original object passed through; swap → `model_copy(update={payload})` fresh copy with `_visibility` popped. **Driver gets exactly one swap; peer broadcast bytes are byte-identical to pre-diff; no double-swap.** reviewer-security independently confirmed the aliasing safety; the e2e (`...broadcasts_raw_to_peers`, which I ran green) asserts it end-to-end.

### OTEL (doctrine) — reachable, not dead

`opening.narration_pov_swapped` (`_watcher_publish`, chargen_mixin:190-202) fires only when `total_swap_count>0`, with 6 attrs (driver_player_id, anchor_pc, anchor_pronouns, swap_count, original/swapped lengths). Reachable from production: the helper is called at line 1572 inside the real `_should_fire_opening_narration` block — exercised by the e2e (`test_watcher_event_emitted_with_attrs_when_swap_fires` unit + the e2e). The GM panel can verify the swap fired. CLAUDE.md OTEL principle satisfied.

### Rule Compliance

Python lang-review (`.pennyfarthing/gates/lang-review/python.md`):
| # | Rule | Verdict |
|---|------|---------|
| 1 | Silent exceptions | PASS — no try/except in the helper |
| 2 | Mutable defaults | PASS — none |
| 3 | Type annotations | PASS — helper fully annotated (`-> list[Any]`, kw-only typed) |
| 6 | Test quality | PASS — specific assertions (swapped text, stripped sidecar, OTEL attrs, no-op cases); e2e behavioral. The alias pyright noise is a false-positive, not a vacuous test |
| 8 | Unsafe deser | N/A — `json.loads` on the model's own `model_dump_json()` (trusted, self-produced) |
| 11 | Input validation / leak | PASS — sidecar consumed-not-leaked; OTEL logs no prose |
| 4,5,7,9,10,12,13,14 | (logging/path/resource/async/import/deps/fix-regress/state-order) | N/A or PASS — none implicated |

Project rules (`sidequest-server/CLAUDE.md`): No Silent Fallbacks — PASS. No Stubbing — PASS. Wire Up What Exists / Don't Reinvent — PASS (reuses the existing swap+pronoun helpers; this is the whole point of the fix). Verify Wiring — PASS (helper called from the real opening block; e2e proves it, run green with PG). Every Test Suite Needs a Wiring Test — PASS (the e2e). OTEL Observability — PASS (the new watcher emit; doctrine explicitly requires it for a narration-subsystem fix, and it's present + reachable).

### Devil's Advocate

Hardest attack — **regress peers / leak.** The broadcast loop feeds peers the original `opening_messages`, which the helper provably never mutates (fresh dicts, model_copy, originals passed through on no-op). Peers can't get the driver-anchored swap; can't double-swap (projection re-anchors per peer independently; live broadcast is raw single-anchor, correct per TEA Finding 1). **Vacuous-test attack:** the `visibility_sidecar` pyright error tempted a "tests don't really exercise the sidecar" conclusion — but I proved the opposite: the swap assertions fire (sidecar populated + serialized as `_visibility`) and the strip is read by field name. The pyright error is alias friction, not a vacuity. **Anchor-confusion attack:** anchor identity is the seated driver's pid against `player_seats`; an anchor≠driver card no-ops (tested). **Dead-OTEL attack:** the emit is reachable from the real opening block and e2e-exercised, gated on swap_count>0. **Env-masking attack (the real one):** the green report claimed the e2e ran when the CI-like env skips it — so I provisioned PG and ran it myself rather than trust the claim; it passes. Nothing the devil surfaced is a functional defect. The only real residue is test-file pyright hygiene (LOW).

### Non-blocking observations
- **[LOW]** +15 new pyright errors in the two new test files (production clean). 2 are `visibility_sidecar` alias false-positives; ~13 are e2e/test type-looseness. Recommend test-file cleanup. Not in the aggregate gate.
- **[INFO]** OTEL swap-count re-derived via a second `swap_to_second_person` call — telemetry-only, deliberate, slightly redundant.
- **[INFO]** GREEN-report claim corrections (e2e skips without PG — I ran it green with PG; ruff repo-wide has 2 pre-existing unrelated errors; pyright +15 test-only). Accuracy, not 71-5 defects.
- Pre-existing `_visibility` egress leak on peer/non-swapped cards → folded into 71-13 (scoped out, acknowledged).

**Data flow traced:** narrator opening → driver: helper swaps anchored card (2nd person), strips sidecar → `out` → driver's socket; peers: original messages → `room.broadcast` (raw 3rd-person, single-anchor correct). Safe at every hop.

**Handoff:** APPROVED → Architect for spec-reconcile → finish. Recommend a quick test-file pyright cleanup (non-blocking) and noting the e2e requires PG to run.