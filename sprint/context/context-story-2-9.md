---
parent: context-epic-2.md
---

# Story 2-9: End-to-End Integration — UI Connects to API, Full Turn Cycle, Narration Renders in Client

## Business Context

This is the payoff story. Everything from Epic 1 and Epic 2 comes together: the React UI
opens a WebSocket to the Rust API, creates a character, takes an action, and sees narrated
response text appear in the game view. This story is about integration testing and fixing
the gaps between what the server produces and what the client expects.

The UI is already complete — it was copied from the working Python app. The API contract
(`docs/api-contract.md`) defines the wire format. If both sides conform to the contract,
this should "just work." In practice, there will be mismatches to resolve.

**UI source:** `sidequest-ui/` (complete React client from sq-2)
**API contract:** `docs/api-contract.md`
**Depends on:** Stories 2-1 through 2-6 (server, session, creation, persistence, orchestrator, agents)

## Technical Approach

### What Needs to Happen

This story is integration, not new feature development. The checklist:

1. **Start both servers** — Rust API on :8765, React dev server on :5173
2. **Connect** — UI opens WebSocket to ws://localhost:8765/ws
3. **Genre selection** — UI fetches GET /api/genres, presents choices
4. **Session connect** — UI sends SESSION_EVENT { event: "connect", player_name, genre, world }
5. **Character creation** — UI renders CHARACTER_CREATION scenes, player makes choices
6. **Game ready** — Server sends SESSION_EVENT { event: "ready" }, UI transitions to game view
7. **Take action** — Player types in InputBar, UI sends PLAYER_ACTION { action: "I look around" }
8. **Thinking indicator** — Server sends THINKING, UI shows animated dinkus
9. **Streaming narration** — Server sends NARRATION_CHUNK messages, UI appends text
10. **Narration complete** — Server sends NARRATION_END with state_delta, UI updates state mirror
11. **State updates** — Server sends PARTY_STATUS, UI updates party panel

### Expected Mismatches to Resolve

Based on experience with contract alignment:

**Message format differences:**
- The UI expects `type` field as SCREAMING_SNAKE (`"PLAYER_ACTION"`). The Rust serde tag
  must use `#[serde(rename = "PLAYER_ACTION")]` — this was done in story 1-2 but needs
  end-to-end verification.
- Payload field naming: UI expects `snake_case` (e.g., `player_name`, `state_delta`).
  Rust serde defaults to snake_case, but verify against every message type.
- `player_id` field: UI sends it as empty string for client-originated messages. Server
  must accept empty string and assign its own.

**State delta format:**
- UI's `useStateMirror` hook expects `state_delta` inside NARRATION and NARRATION_END payloads.
  Server must include this field.
- Characters in delta are merged by `name` — names must match exactly.
- Quests in delta are merged by key — keys must be stable strings.

**Session lifecycle:**
- UI stores session data in localStorage and attempts reconnection on page refresh.
  Server must handle reconnection (same player_name, new WebSocket) gracefully.
- UI expects `has_character` boolean in SESSION_EVENT connected response.
- UI expects `initial_state` object in SESSION_EVENT ready response for returning players.

**Character creation:**
- UI expects `phase`, `scene_index`, `total_scenes`, `narration`, `input_type`, `choices`
  fields in CHARACTER_CREATION payload.
- `input_type` is `"choice"` or `"freeform"` — must match exactly.
- `choices` array contains `{ label, description }` objects.

### Testing Strategy

**Manual smoke test (the real test):**
1. `just api-run` in one terminal
2. `just ui-dev` in another
3. Open browser to localhost:5173
4. Play through: connect → create character → take 3 actions → verify narration appears

**Automated integration test:**

```rust
#[tokio::test]
async fn test_full_turn_cycle() {
    // 1. Start server on random port
    let (addr, _handle) = start_test_server().await;

    // 2. Connect WebSocket
    let (mut ws, _) = tokio_tungstenite::connect_async(format!("ws://{}/ws", addr)).await.unwrap();

    // 3. Send SESSION_EVENT connect
    ws.send(Message::Text(serde_json::to_string(&GameMessage::SessionEvent(
        SessionEventPayload { event: "connect".into(), player_name: "Test".into(), genre: "mutant_wasteland".into(), world: "flickering_reach".into(), .. }
    )).unwrap())).await.unwrap();

    // 4. Expect SESSION_EVENT connected
    let msg = read_message(&mut ws).await;
    assert!(matches!(msg, GameMessage::SessionEvent(p) if p.event == "connected"));

    // 5. Handle character creation scenes (auto-select first choice)
    loop {
        let msg = read_message(&mut ws).await;
        match msg {
            GameMessage::CharacterCreation(p) if p.phase == "scene" => {
                // Send choice "1"
                ws.send(/* CHARACTER_CREATION choice */);
            }
            GameMessage::CharacterCreation(p) if p.phase == "confirmation" => {
                // Send confirm
                ws.send(/* CHARACTER_CREATION confirm */);
            }
            GameMessage::CharacterCreation(p) if p.phase == "complete" => break,
            GameMessage::SessionEvent(p) if p.event == "ready" => break,
            _ => continue,
        }
    }

    // 6. Send PLAYER_ACTION
    ws.send(Message::Text(serde_json::to_string(&GameMessage::PlayerAction(
        PlayerActionPayload { action: "I look around the tavern".into(), aside: false }
    )).unwrap())).await.unwrap();

    // 7. Expect THINKING → NARRATION_CHUNK* → NARRATION_END
    let mut got_thinking = false;
    let mut got_chunks = false;
    let mut got_end = false;
    loop {
        let msg = read_message(&mut ws).await;
        match msg {
            GameMessage::Thinking(_) => got_thinking = true,
            GameMessage::NarrationChunk(_) => got_chunks = true,
            GameMessage::NarrationEnd(p) => {
                got_end = true;
                // Verify state_delta exists (may be None if nothing changed)
                break;
            }
            _ => {} // PARTY_STATUS, etc.
        }
    }
    assert!(got_thinking);
    assert!(got_end);
    // got_chunks may be false if response is very short
}
```

This test requires Claude CLI to be available. For CI, mock the `ClaudeClient` behind the
`GameService` trait to return canned responses.

### UI Adjustments (if needed)

The UI should work as-is since it was built against the same API contract. However, if minor
adjustments are needed:

- **CORS:** UI's WebSocket connection may need the server's CORS to allow upgrade headers
- **Genre list:** UI's ConnectScreen fetches `/api/genres` — the response format must match
- **Binary frames:** UI expects voice audio as binary frames. The server can skip these for now (no daemon), but must not crash if the UI sends VOICE_SIGNAL messages.

**We do NOT rewrite the UI in this story.** If there's a contract mismatch, the server
adjusts to match what the UI expects (the UI is the existing, working client).

### Cross-Repo Coordination

This story touches both repos:
- `sidequest-api` — server-side fixes for contract alignment
- `sidequest-ui` — only if absolutely necessary (e.g., a URL change)

The API contract (`docs/api-contract.md`) is the source of truth. Both sides conform to it.

## Scope Boundaries

**In scope:**
- End-to-end manual testing: connect → create → play → narrate
- Wire format verification: every message type matches api-contract.md
- Integration test: automated WebSocket test with full turn cycle
- Contract mismatch fixes (server adjusts to match UI expectations)
- `just api-run` and `just ui-dev` work together
- CORS configuration verified working with React dev server

**Out of scope:**
- UI code changes (unless contract mismatch requires it)
- Combat overlay testing (requires combat agent producing correct patches)
- Map/inventory/journal testing (requires world state agent)
- Audio/voice testing (daemon not connected)
- Performance testing
- Production deployment

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Servers start | `just api-run` and `just ui-dev` both start without errors |
| UI connects | Browser opens localhost:5173, WebSocket connects to :8765 |
| Genre list | ConnectScreen shows available genres from /api/genres |
| Session connects | Player enters name, selects genre/world, gets "connected" response |
| Character creation | Creation scenes render, player makes choices, character built |
| Game ready | After creation, game view appears with narrative display |
| Action works | Player types action, THINKING indicator shows |
| Narration streams | Narration text appears in NarrativeView (streaming or batch) |
| State updates | PARTY_STATUS shows character in party panel after turn |
| Reconnection | Page refresh → UI reconnects, resumes session (if save exists) |
| No crashes | Unknown message types logged, not crashed on |
| Integration test | Automated test passes: connect → create → action → narration |

## Notes

This story will likely surface issues in earlier stories (2-1 through 2-6). That's expected
and desirable — integration testing is where implementation meets reality. Fixes should be
made in the appropriate story's code, not hacked around in this story.

The goal is not pixel-perfect feature parity with the Python server. The goal is: the core
loop works. A player can connect, create a character, take an action, and read a narrated
response. Everything else is polish for later stories and epics.
