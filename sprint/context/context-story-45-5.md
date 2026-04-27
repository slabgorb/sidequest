---
parent: sprint/epic-45.yaml
workflow: tdd
---

# Story 45-5: Stale-slot reuse on session reinit blocks turn 1

## Business Context

**Playtest 3 evidence (2026-04-19, evropi session):** the `prot_thokk` and
`hant` save files were created at 2026-04-19T16:31 UTC, yet their
`narrative_log` table held only a single row dated 2026-04-18 — prior-day
narrative bleeding through a session that was nominally fresh. The
`turn_manager` was frozen at `round=0/interaction=2`,
`last_played == created_at`, and Turn 1 never fired. The session had
inherited the stale prior-day narrative without the snapshot or
turn-counter that produced it, so the slug was wedged: chargen-complete
flipped state to `Playing`, but the first `_execute_narration_turn()` call
saw a populated `narrative_log` and a counter that disagreed with the
log's `max(round_number)`. The narrator could not bootstrap.

This is the **coal-as-diamond** failure (ADR-014) that Sebastien's GM
panel must catch — `last_played == created_at` is a load-bearing
mechanical fact (the session never actually ran a turn), but absent an
OTEL span it looks normal until you read SQL by hand. James loses
narrative continuity twice over: prior-day text smuggled into a "fresh"
slug; first-turn bootstrap silently wedged. Alex feels it as a session
that just refuses to start. ADR-023 (Session Persistence) declares that
auto-save is atomic per turn; the corollary it forgot is that
**re-init must be atomic too** — either every per-slot table is wiped, or
re-init refuses to write into a populated slot. ADR-085 (port-drift)
applies: this `init_session` path was ported from the Rust tree and
inherited the half-clear (session_meta replaced, log not).

## Technical Guardrails

- **Outermost reachable seam:** `SqliteStore.init_session()` at
  `sidequest/game/persistence.py:260–269` and its two call sites in the
  session_handler — the legacy non-slug new-session branch at
  `sidequest/server/session_handler.py:2154` and the slug-keyed
  new-session branch at `session_handler.py:1654`. The TDD test must
  exercise one of these call sites end-to-end (open a populated `.db`
  on disk, drive the new-session branch, assert post-state) — a unit
  test on a `clear_session_tables()` helper alone fails the wire test
  bar.

- **The current half-clear:** `init_session()` issues
  `INSERT OR REPLACE INTO session_meta (id, ...) VALUES (1, ?, ?, ?, ?, 1)`
  (`persistence.py:264–268`). It overwrites `session_meta` row 1 but
  leaves `game_state` (id=1, single-row table), `narrative_log`
  (append-only), `scrapbook_entries`, `lore_fragments`, `events`, and
  `projection_cache` untouched. That is the seam where prior-day rows
  survive. The schema lives at `persistence.py:73–149`.

- **Two acceptable fixes — pick the one Keith picks:**
  1. **Clear-on-reinit (TDD-natural).** Wrap `init_session()` in a
     transaction that `DELETE`s every per-slot table (`game_state`,
     `narrative_log`, `scrapbook_entries`, `lore_fragments`, `events`,
     `projection_cache`) before the `INSERT OR REPLACE` on
     `session_meta`. The `games` table (slug-keyed) and the global
     schema do not need to clear. Single transaction; either every
     table clears or none does.
  2. **Refuse-on-populated.** `init_session()` checks for any row in
     `narrative_log` / `game_state` and raises `PersistError` (or a new
     `StaleSlotError`) so the caller can route to a typed error frame.
     Closer to the SOUL.md "no silent fallbacks" line, but it requires a
     UX path to recover (move-the-save-aside flow already exists for
     `SaveSchemaIncompatibleError` at `persistence.py:22–47`, model on
     that).

  TDD spec the chosen fix; do not ship both.

- **Reuse, don't reinvent:** `SaveSchemaIncompatibleError` at
  `persistence.py:22–47` is the exact precedent for the refuse-on-populated
  branch — typed exception, typed ERROR frame, save-path in the message.
  Mirror that shape if option 2 is chosen.

- **Turn-manager freeze is a symptom, not the bug.** The reported
  `round=0/interaction=2` suggests the prior session crashed mid-turn
  and the partial counter was preserved in `game_state.snapshot_json`.
  Once the slot-clear (or refuse) fix lands, the symptom goes away
  because chargen-confirm runs `materialize_from_genre_pack` →
  `replace_with()` (`session_handler.py:2680`), which writes a fresh
  `TurnManager(round=1, interaction=1)` (defaults at
  `sidequest/game/turn.py:54–56`). Do not add a separate "reset
  TurnManager" path — that would mask the underlying lifecycle bug.

- **OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md):** Define
  in `sidequest/telemetry/spans.py` and register `SPAN_ROUTES` entries
  using the existing pattern (e.g., `SPAN_GAME_HANDSHAKE_DELTA_APPLIED`
  at `spans.py:331–332`, `SPAN_NPC_AUTO_REGISTERED` at line 259):
  | Span | Attributes | Site |
  |------|------------|------|
  | `session.slot_reinitialized` | `genre_slug`, `world_slug`, `slug`, `cleared_tables` (list of table names), `prior_narrative_count`, `prior_event_count`, `mode` (`"clear"` or `"refuse"`) | `init_session()` after the clear (or before raising on refuse) |
  | `session.slot_reuse_rejected` | `genre_slug`, `world_slug`, `slug`, `prior_last_played`, `prior_created_at` | refuse path only |

  The first span MUST fire on every reinit, even when prior counts are
  zero — Sebastien's GM panel needs the negative confirmation that
  reinit ran cleanly, not just that it ran at all.

- **Test fixtures:** `session_handler_factory()` in
  `sidequest-server/tests/server/conftest.py:332` and
  `_FakeClaudeClient` in `conftest.py:197` are the multiplayer-friendly
  test fixtures — chargen completes deterministically without an LLM
  call. The TDD test should populate a `.db` directly via
  `SqliteStore.open(path)` + `append_narrative()`, then drive the
  new-session branch through `_handle_connect`/slug-resume so the
  reinit path actually runs.

- **Test files (where new tests should land):**
  - New: `tests/server/test_init_session_clears_stale_slot.py` —
    populates a `.db`, calls `init_session()`, asserts every per-slot
    table is empty (or the refuse-path raises).
  - New or extend `tests/server/test_chargen_persist_and_play.py` — the
    end-to-end wiring test: pre-populate slot, connect via slug, drive
    chargen, assert Turn 1 fires and `narrative_log` has exactly one
    chargen-era row at `round=1`.

## Scope Boundaries

**In scope:**

- One of the two fixes above to `SqliteStore.init_session()`
  (`persistence.py:260`).
- Both call sites at `session_handler.py:1654` and
  `session_handler.py:2154` covered — clearing the legacy path while
  leaving the slug path stale (or vice versa) is exactly the kind of
  asymmetric fix that lets coal back into the system.
- New OTEL spans `session.slot_reinitialized` and (refuse-path)
  `session.slot_reuse_rejected`, registered in `SPAN_ROUTES`.
- TDD-first test: failing test that populates a `.db` and drives the
  reinit branch, then the implementation that makes it pass.
- Wiring test: chargen → first-turn-fires end-to-end on a slot that was
  populated before connect.

**Out of scope:**

- Migrating existing on-disk save files. Players whose `.db` is in this
  wedged state can move the file aside; no auto-migration.
- Reworking `TurnManager` defaults or its serialization. The frozen
  `round=0/interaction=2` is a downstream symptom that disappears with
  the upstream fix.
- Restructuring the `events` / `projection_cache` lifecycle. They
  clear with the rest of the per-slot tables (option 1) or block the
  reinit (option 2); the broader event-log decomposition is out.
- UI work. The refuse-path's typed error frame piggybacks on the
  existing `code="save_schema_invalid"` UX (`session_handler.py:2128–2136`)
  with a new `code="slot_populated"` — no new UI states.
- Multi-player slot semantics. Slug-keyed re-init clears all peers'
  per-slot tables together; per-player partial clears are an explicit
  anti-goal.

## AC Context

The story title carries the contract; expanded into testable ACs:

1. **`init_session()` either clears every per-slot table atomically OR
   refuses to write into a populated slot.**
   - Positive test: a slot with existing rows in `narrative_log`,
     `game_state`, `scrapbook_entries`, `lore_fragments`, `events`, and
     `projection_cache` is reinitialized; post-state has zero rows in
     each (clear path) OR `init_session()` raised the typed error and
     none of those rows changed (refuse path).
   - Negative test: a fresh slot (zero rows in all tables) reinits
     cleanly under both options — clear is a no-op, refuse permits.
     This is the regression guard against an over-eager refuse path
     blocking legitimate first-time connects.

2. **Turn 1 fires on a slot that was populated before connect.**
   - Wire-test: populate slot with stale narrative, drive
     `_handle_connect` → chargen → `_chargen_confirmation()` → first
     `_execute_narration_turn()`. Assert `turn_manager.round == 1`,
     `turn_manager.interaction == 2` (post-first-turn), and
     `last_played > created_at`.
   - Negative test: same flow without the fix → either Turn 1 wedges
     (clear-path TDD failure) or `init_session()` raises and the
     wire-test catches the typed error (refuse-path TDD failure). The
     test fails before the fix, passes after.

3. **OTEL `session.slot_reinitialized` fires on every reinit with
   accurate prior-counts.**
   - Test: populated slot triggers reinit, assert span fires once with
     `prior_narrative_count > 0`, `cleared_tables` listing every table
     touched.
   - Test: fresh slot triggers reinit, assert span fires once with
     `prior_narrative_count == 0` — the negative confirmation
     Sebastien needs.
   - Test: `SPAN_ROUTES` mapping is registered so the watcher hub sees
     the event.

4. **Existing not-stale-slot paths are unchanged.**
   - Regression test: `tests/server/test_chargen_persist_and_play.py`
     equivalent passes pre- and post-fix on the happy path (fresh
     slot, chargen, first turn fires). The fix must not break the
     load-resume path (`saved is not None` branch at
     `session_handler.py:2138`) — that path does NOT call
     `init_session()` and must continue to skip clear/refuse logic.
