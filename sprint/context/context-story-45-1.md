---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-1: Sealed-letter world-state handshake — shared-world delta between turns

## Business Context

**Playtest 3 evidence (2026-04-19):** During multiplayer narration, Orin's narrator
fabricated a "collapsed corridor" separating Orin from Blutka because Orin's
`state_summary` JSON didn't ground-truth Blutka's adjacency. The narrator filled
the silence by inventing a physical separation rather than admitting "Blutka is
right next to you." This is the classic Illusionism failure (SOUL.md) — the
narrator takes liberty with shared-world facts because it's not given them.

ADR-037 declared the room owns the canonical snapshot; ADR-085 noted this
shared-world handshake never made it across the Rust→Python port. Story 37-37
was the original spec; this story re-scopes 37-37 onto the live Python tree.

The fix is invisible to players (AC #4): the narrator stops fabricating
separations because it now sees ground-truth adjacency in its prompt.

## Technical Guardrails

- **Outermost reachable layer:** `_execute_narration_turn()` (session_handler.py:3251–3390) and
  `_build_turn_context()` (session_helpers.py:143–243). The boundary test must
  exercise this seam — a unit test on a `merge_shared_delta()` helper alone
  fails the wire-first gate.
- **Emit point:** After `snapshot.turn_manager.record_interaction()` in
  `_execute_narration_turn()`. The turn-end broadcast (`NarrationEndMessage`) already
  has a `state_delta` field that is currently `None` — wire it.
- **Apply point:** Inside `_build_turn_context()` (session_helpers.py), BEFORE
  `state_summary = snapshot.model_dump_json()` (line ~221). This is the JSON the
  narrator sees; that's the seam where ground-truth must be injected.
- **OTEL pattern:** Add `SPAN_GAME_HANDSHAKE_DELTA_APPLIED = "game.handshake.delta_applied"`
  to `sidequest/telemetry/spans.py`, register a SPAN_ROUTES entry with
  `event_type="game.handshake.delta_applied"`, `component="game"`, and call
  `span.add_event(...)` from the merge site. Conflict events go through
  `_watcher_publish` so the GM panel can see resolution strategy in real time.
- **Canonical vs Perceived split (load-bearing):**
  - **Canonical (delta carries, overwrites local on merge):** `location`/`room_id`,
    `discovered_regions`, active encounter id, party formation
    (`{player_id, location, adjacency_graph}`).
  - **Perceived (POV-only, NEVER touched by merge):** mood, tactics, NPC dispositions
    perceived by this character, what peers are feeling. PartyPeer (session.py:147–177)
    is already the canonical identity packet — extend it for adjacency, do NOT add
    perception fields to it.
- **Reuse, don't reinvent:** `PartyPeer.from_character()` (session.py:169) projects
  canonical identity. `_resolve_acting_character_name()`, `_resolve_location_display()`,
  and `compute_delta()` (game/delta.py:134) already exist — wire through them.
- **Test harness:** `session_handler_factory()` in `tests/server/conftest.py:330` is the
  multiplayer fixture. `_FakeClaudeClient` (conftest.py:195) returns canned narrator
  output so tests don't hit the real LLM.
- **No schema migration:** Runtime-only handshake. `SharedWorldDelta` is an in-memory
  dataclass / pydantic model emitted on each turn; it is not persisted on its own
  (the GameSnapshot already persists location/encounter).

## Scope Boundaries

**In scope:**
- New `SharedWorldDelta` model (location, encounter id, party formation/adjacency).
- `build_shared_world_delta(snapshot) -> SharedWorldDelta` (extract from canonical
  snapshot post-turn).
- `merge_shared_delta_into_snapshot(snapshot, delta) -> MergeResult` (apply to
  next player's read view; record conflicts).
- Wire `build_shared_world_delta` into `_execute_narration_turn()` after
  `record_interaction()`; populate `NarrationEndPayload.state_delta`.
- Wire `merge_shared_delta_into_snapshot` into `_build_turn_context()` before
  `state_summary` JSON serialization (only when prior delta is available).
- New OTEL span `game.handshake.delta_applied` with attributes
  `delta_fields`, `conflict_count`, `resolution_path`. Register SPAN_ROUTES entry.
- Conflict watcher events (component="game", severity per resolution path).

**Out of scope:**
- UI changes (AC #4 explicit). If `NarrationEndMessage.state_delta` is not yet
  rendered client-side, that is a follow-up story.
- Persisted-storage schema migrations. Delta is runtime-only.
- Reworking PartyPeer to add perception fields — explicit anti-goal.
- Cross-save delta sync (delta is intra-session/intra-room only).
- Narrator prompt re-engineering — only the data going into the existing
  `state_summary` JSON changes; the prompt template does not.

## AC Context

1. **Server emits shared-world delta payload after each turn.**
   - Test exercises `_execute_narration_turn()` end-to-end, asserts the
     broadcast `NarrationEndMessage.payload.state_delta` is non-None and contains
     `location`, `encounter_id`, and `party_formation` (a list keyed by
     `player_id`).
   - Adjacency for at least the active player MUST be present.

2. **Delta is applied to subsequent player's game_state before narrator context injection.**
   - Test exercises `_build_turn_context()` for player B after player A's turn.
   - The `state_summary` JSON the orchestrator receives MUST include party
     adjacency reflecting player A's new location.
   - Without the merge, `state_summary` would describe the world as it was at
     player B's last narration — that's the bug the story closes.

3. **OTEL span `game.handshake.delta_applied` fires on merge.**
   - Span attributes: `delta_fields` (list of canonical field names changed),
     `conflict_count` (int, 0 in normal case), `resolution_path`
     (e.g., "delta_authoritative", "no_change", "conflict_logged").
   - Conflict events emitted via `_watcher_publish` when delta contradicts
     local state — enumerate the resolution choice (e.g., "delta_overwrote_local").
   - GM panel must see at least one event per merge so the lie detector works.

4. **No narration changes required — fix is invisible to players.**
   - Negative test: perceived state (mood, tactics, character.core) is NOT
     mutated by the merge. Snapshot identity for non-canonical fields is
     unchanged after `merge_shared_delta_into_snapshot()`.
