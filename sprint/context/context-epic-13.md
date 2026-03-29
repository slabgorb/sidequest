# Epic 13: Sealed Letter Turn System — Simultaneous Input Collection with Player Visibility

## Overview

The current multiplayer turn system has the infrastructure (TurnBarrier, MultiplayerSession,
TurnMode state machine from Epic 8) but the player experience is broken. Today's behavior:
one player acts, everyone locks until the narrator responds, then it's a free-for-all race to
type next. No visibility into what others did. No indication of who still needs to go.

The sealed letter pattern fixes this: all players submit actions blindly, the UI shows who
has and hasn't submitted, actions are revealed together, and the narrator processes the full
batch as a single turn. This is the core multiplayer mechanic — everything else is polish
until this works.

## Background

### What Already Exists (from Epic 8)

| Component | Status | File |
|-----------|--------|------|
| **MultiplayerSession** | Working | `sidequest-game/src/multiplayer.rs` |
| **TurnBarrier** | Working | `sidequest-game/src/barrier.rs` |
| **TurnMode** (FreePlay/Structured/Cinematic) | Working | `sidequest-game/src/turn_mode.rs` |
| **SharedGameSession** with broadcast channel | Working | `sidequest-server/src/shared_session.rs` |
| **TURN_STATUS** message type | Defined | `sidequest-protocol/src/message.rs` |
| **Party action composition** | Working | Epic 8, story 8-4 |

The backend can already collect actions, wait for a barrier, and compose a batched prompt.
What's missing:

1. **Actions are not held** — each PLAYER_ACTION currently triggers an independent orchestrator
   call instead of being queued until the barrier resolves
2. **No action reveal** — other players never see what action triggered a narration
3. **No submission status UI** — players have no visibility into who's submitted
4. **Timeout is silent** — auto-filled actions happen without notification

### Playtest Evidence (2026-03-29)

> "One player will take their turn. It will then lock for everybody until the narrator comes
> back and then it's a free-for-all. Whoever wants to type in first gets the narrator again,
> everybody else has to wait."

> "Players have trouble figuring out what the other player is doing to elicit the prompt that
> the other player got."

### Python Reference

sq-2's turn manager implemented the sealed letter pattern with:
- `collect_actions()` — gathers from all connected clients
- `compose_party_actions()` — formats as PARTY ACTIONS block
- Action reveal via `TurnSummary` message type
- Visual turn status in the React client

## Technical Architecture

### Message Flow (Target State)

```
Player A submits action ───► Server holds in MultiplayerSession.actions
                              │
                              ├─ Broadcast TURN_STATUS {player: "A", status: "submitted"}
                              │  (UI updates: A's indicator → ✓)
                              │
Player B submits action ───► Server holds in MultiplayerSession.actions
                              │
                              ├─ Broadcast TURN_STATUS {player: "B", status: "submitted"}
                              │  (UI updates: B's indicator → ✓)
                              │
                              ├─ Barrier met (all players submitted)
                              │
                              ├─ Broadcast ACTION_REVEAL {
                              │    actions: [
                              │      {character: "Thane", action: "I search the merchant's cart"},
                              │      {character: "Lyra", action: "I keep watch for guards"}
                              │    ]
                              │  }
                              │
                              ├─ Compose batched prompt → Orchestrator
                              │
                              └─ Orchestrator → Narrator → NARRATION broadcast
```

### New Protocol Messages

```rust
// Server → Client: reveal all submitted actions
ActionReveal {
    actions: Vec<PlayerActionEntry>,  // character_name + action_text
    turn_number: u64,
    auto_resolved: Vec<String>,       // character names that timed out
}

// Server → Client: DM turn control acknowledgment
DmTurnControl {
    action: String,  // "force_resolve" | "extend_timeout"
    detail: String,  // e.g., "extended by 30s"
}
```

### Key Changes to Existing Code

**`dispatch_player_action()` in `lib.rs`:**
- Current: immediately calls orchestrator with single action
- Target: in Structured mode, call `session.submit_action()`, broadcast TURN_STATUS,
  only call orchestrator when barrier resolves

**`SharedGameSession`:**
- Add `broadcast_action_reveal()` method
- Add `pending_players()` → TURN_STATUS broadcast on each submission

**`MultiplayerSession`:**
- `submit_action()` already returns `TurnStatus::Resolved` vs `TurnStatus::Pending`
- Need to add `auto_resolved_players` tracking when timeout fires

### UI Components (sidequest-ui)

**TurnStatusPanel** (new component):
- Shows each player's name + submission state (pending / submitted / auto-resolved)
- Updates via TURN_STATUS WebSocket messages
- Compact horizontal layout, always visible during Structured mode

**ActionRevealBlock** (new component):
- Renders above narrator response
- Shows each character's action as a brief card
- Auto-resolved actions shown with subtle "waited" indicator

**Turn Mode Indicator** (new component):
- Small badge showing current mode
- Tooltip explains mode behavior
- Animates on transition

## Story Dependency Graph

```
Epic 8 (done)
 │
 ├──► 13-1 (turn collection UI — shows who submitted)
 │     │
 │     └──► 13-2 (server holds actions until barrier)
 │           │
 │           ├──► 13-3 (action reveal broadcast + UI)
 │           │     │
 │           │     └──► 13-7 (integration test)
 │           │
 │           ├──► 13-4 (timeout fallback + notification)
 │           │
 │           └──► 13-6 (DM force-resolve / extend)
 │
 └──► 13-5 (turn mode indicator — parallel)
```

## Deferred (Not in This Epic)

- **Cinematic mode UX** — Narrator-paced prompts where players respond to specific questions.
  The turn mode exists; the UX for it is a separate concern.
- **Player-to-player private messaging** — Out of scope, players use voice chat.
- **Action voting/reaction** — Other players reacting to submitted actions before narrator
  processes. Interesting but unnecessary complexity.
- **Split-party turns** — When players are in different locations, they could have independent
  turn cycles. Deferred until party splitting is a designed mechanic.

## Success Criteria

During a multiplayer session:
1. All players see who has and hasn't submitted their action
2. No player can "race" to submit — everyone submits once per turn
3. After barrier resolves, all players see what each character did before narration begins
4. Timeout auto-fills missing players and notifies the party who was auto-resolved
5. DM can force-resolve or extend timeout at any time
6. Turn mode indicator shows the current mode with explanation
7. The narrator's response references all submitted actions, not just the fastest typist's
