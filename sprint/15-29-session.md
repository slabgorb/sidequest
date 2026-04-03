---
story_id: "15-29"
jira_key: ""
epic: "15"
workflow: "tdd"
---
# Story 15-29: Wire append_narrative to SQLite — narrative_log table never written to

## Story Details
- **ID:** 15-29
- **Epic:** 15 (Playtest Debt Cleanup — Stubs, Dead Code, Disabled Features)
- **Jira Key:** (Personal project — no Jira)
- **Workflow:** tdd
- **Priority:** p2
- **Points:** 2
- **Stack Parent:** none
- **Depends On:** 15-8 (completed 2026-04-01)

## Problem Statement

`persist_game_state()` in `sidequest-server/dispatch/mod.rs:1460-1539` does two things:

1. **Appends narration to in-memory snapshot:** Line 1471 pushes a NarrativeEntry into `ctx.snapshot.narrative_log` (a Vec<NarrativeEntry> inside the GameSnapshot JSON blob)
2. **Saves the snapshot to SQLite:** Lines 1500-1508 call `ctx.state.persistence().save()` to persist the snapshot blob

However, the **dedicated narrative_log SQLite table** (created by the persistence schema) is never written to. The `append_narrative()` method exists in `PersistenceHandle` (persistence.rs:558-570) and has full actor-pattern plumbing, but has **zero non-test callers** in sidequest-server.

This means:
- `recent_narrative()` always returns an empty Vec (querying the SQLite table)
- "Previously On..." recaps cannot be generated
- Session reconnects have no narrative context to display

## Solution

After appending the narration entry to `ctx.snapshot.narrative_log` in `persist_game_state()`, also call `ctx.state.persistence().append_narrative()` to write the entry to the SQLite table.

### Key Changes

1. **In persist_game_state() (dispatch/mod.rs:1460-1539):**
   - After line 1480 (push to snapshot.narrative_log), call `ctx.state.persistence().append_narrative(ctx.genre_slug, ctx.world_slug, ctx.player_name_for_save, &entry)` to write to SQLite
   - Add OTEL event: `persistence.narrative_appended` with fields: turn, content_length

2. **Wire verification:**
   - Verify the call is made on every turn in `persist_game_state()`
   - Verify OTEL event emits to GM panel
   - Integration test: play a full turn, verify `recent_narrative()` returns the entry

## Technical Context

- **NarrativeEntry** is defined in `sidequest-game/src/narrative.rs` and has fields: timestamp, round, author, content, tags, encounter_tags, speaker, entry_type
- **append_narrative()** in PersistenceHandle is async and takes genre_slug, world_slug, player_name, and NarrativeEntry
- The call signature is: `persistence.append_narrative(genre, world, player_name, &entry).await`
- persist_game_state() is already async and awaits the save() call, so adding await for append_narrative() is straightforward

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-02T20:35:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T20:35:00Z | - | - |

## Delivery Findings

No upstream findings at this time.

## Design Deviations

None at this time.

## Implementation Notes

### Files to Modify

- **crates/sidequest-server/src/dispatch/mod.rs**
  - Modify `persist_game_state()` function (starting at line 1460)
  - After appending to snapshot.narrative_log (line 1471-1480), call `ctx.state.persistence().append_narrative()` with the same entry
  - Add OTEL event emission for `persistence.narrative_appended` event

### Testing Strategy

1. **Unit test** — verify persist_game_state() calls append_narrative() with correct parameters
2. **Integration test** — single turn dispatch, verify recent_narrative() returns the appended entry
3. **Wiring test** — verify non-test callers exist for append_narrative()

### Wiring Verification

- Non-test callers of `append_narrative()`: will be added in persist_game_state() (dispatch/mod.rs:~1480)
- OTEL event: `persistence.narrative_appended` emitted after append_narrative() succeeds
- Recap generation: recent_narrative() can now be called to populate "Previously On..." on session reconnect

