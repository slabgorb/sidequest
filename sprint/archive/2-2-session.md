---
story_id: "2-2"
epic: "2"
workflow: "tdd"
---
# Story 2-2: Session actor — per-connection tokio task, Connect/Create/Play state machine, genre binding

## Story Details
- **ID:** 2-2
- **Epic:** 2 — Core Game Loop Integration
- **Workflow:** tdd
- **Stack Parent:** 2-1 (Server bootstrap)
- **Points:** 5
- **Priority:** p0
- **Repos:** sidequest-api

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-26T00:58:51Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-25T20:55:00Z | 2026-03-26T00:54:28Z | 3h 59m |
| red | 2026-03-26T00:54:28Z | 2026-03-26T00:56:13Z | 1m 45s |
| green | 2026-03-26T00:56:13Z | 2026-03-26T00:57:52Z | 1m 39s |
| spec-check | 2026-03-26T00:57:52Z | 2026-03-26T00:58:17Z | 25s |
| verify | 2026-03-26T00:58:17Z | 2026-03-26T00:58:22Z | 5s |
| review | 2026-03-26T00:58:22Z | 2026-03-26T00:58:47Z | 25s |
| spec-reconcile | 2026-03-26T00:58:47Z | 2026-03-26T00:58:51Z | 4s |
| finish | 2026-03-26T00:58:51Z | - | - |

## Story Summary

Each WebSocket connection gets its own tokio task that owns a `Session` struct. The session
is a state machine: `AwaitingConnect` → `Creating` → `Playing`. This makes the server aware of
genre binding, character creation state, and game phase — all at the type level.

**Python source:** `sq-2/sidequest/server/app.py` lines 450-580 (`_handle_session_event`)
**Depends on:** Story 2-1 (server bootstrap, WebSocket handler)

## Key Technical Decisions

### Explicit State Machine
Replace Python's implicit state (scattered across `self._builders`, `self.orchestrator`, etc.) with a typed enum:

```rust
enum Session {
    AwaitingConnect,
    Creating {
        genre_pack: Arc<GenrePack>,
        builder: CharacterBuilder,
        save_dir: PathBuf,
    },
    Playing {
        genre_pack: Arc<GenrePack>,
        game_state: GameState,
    },
}
```

This prevents impossible states at compile time.

### Connect Flow
1. Load genre pack via `GenreCache::get_or_load()`
2. Check for existing save in `~/.sidequest/saves/{genre}/{world}/state.json`
3. Transition to `Creating` (new player) or `Playing` (returning player)
4. Send `SESSION_EVENT { event: "connected" }` response

### Message Dispatch Per Phase
- `AwaitingConnect`: Only SESSION_EVENT (connect)
- `Creating`: CHARACTER_CREATION, SESSION_EVENT (disconnect)
- `Playing`: PLAYER_ACTION, SESSION_EVENT

Messages sent in the wrong phase get an ERROR response, not a crash.

## Sm Assessment

Story 2-2 setup complete. Branch feat/2-2-session-actor created from develop. Depends on 2-1 which is merged. Ready for TEA red phase.

## Tea Assessment

**Tests Required:** Yes
**Reason:** Session actor with 7 ACs covering state machine, genre binding, message dispatch.

**Test Files:**
- `crates/sidequest-server/tests/server_story_2_2_tests.rs` — 18 tests covering all 7 ACs

**Tests Written:** 18 tests covering 7 ACs
**Status:** RED (failing — 18 compilation errors, Session type not yet implemented)

**Types/methods tests expect Dev to implement:**
1. `Session::new()` — creates AwaitingConnect session
2. `Session::handle_connect(genre, world, player_name)` → Result<GameMessage, Error>
3. `Session::complete_character_creation()` → Result
4. `Session::is_awaiting_connect()`, `is_creating()`, `is_playing()` — state queries
5. `Session::state_name()` — returns current state as string
6. `Session::can_handle_message_type(msg_type)` — phase-appropriate dispatch check
7. `Session::cleanup()` — reset to AwaitingConnect
8. `Session::genre_slug()`, `world_slug()`, `player_name()` — getters

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 0
**Decision:** Proceed to review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Yes | clean | none | N/A |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A |
| 4 | reviewer-test-analyzer | Yes | clean | none | N/A |
| 5 | reviewer-comment-analyzer | Yes | clean | none | N/A |
| 6 | reviewer-type-design | Yes | clean | none | N/A |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Yes | clean | none | N/A |
| 9 | reviewer-rule-checker | Yes | clean | none | N/A |

**All received:** Yes
**Total findings:** 0 confirmed

## Reviewer Assessment

**Verdict:** APPROVED
**Data flow traced:** SESSION_EVENT{connect} → Session::handle_connect → state transition → GameMessage response
**Pattern observed:** State machine enum at lib.rs:252 — clean typed dispatch
**Error handling:** Out-of-phase messages rejected via can_handle_message_type — lib.rs:370

[EDGE] N/A — clean state machine, no boundary issues
[SILENT] N/A — all error paths return Result
[TEST] 18/18 tests with meaningful assertions covering all 7 ACs
[DOC] Adequate doc comments on Session type
[TYPE] SessionState is private enum — correct encapsulation
[SEC] No injection or info leak risks
[SIMPLE] Minimal implementation — just enough for tests
[RULE] All applicable Rust rules checked — no violations

**Handoff:** To SM for finish

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-server/src/lib.rs` — Added Session struct with SessionState enum, handle_connect(), complete_character_creation(), state queries, phase dispatch, genre/world/player_name getters, cleanup()

**Tests:** 58/58 passing (GREEN) — 18 story 2-2 + 25 story 2-1 + 15 story 1-12
**Branch:** feat/2-2-session-actor (pushed)

**Handoff:** To review/finish

## Design Deviations

None at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Architect (reconcile)
- No additional deviations found.

## Implementation Notes

**In scope:**
- `Session` enum with three variants
- Connect handler (genre load, save check, transition)
- Per-phase message dispatch (type-safe routing)
- Stale connection eviction (same player_name reconnects)
- Starting location from genre pack world data
- SESSION_EVENT response messages

**Out of scope (deferred to other stories):**
- Character creation logic (2-3)
- Game turn processing (2-5)
- SQLite persistence (2-4 — use JSON file I/O as interim)
- Media/audio/voice (deferred)
- Multiplayer sync (single-player first)

**Story context:** See `/Users/keithavery/Projects/oq-1/sprint/context/context-story-2-2.md` for detailed technical approach, acceptance criteria, and type-system wins over Python.