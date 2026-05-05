# Solo Sealed Action Turn — Sequence

> **Last updated:** 2026-05-05 (post-port; ADR-082)
>
> Module paths reference `sidequest-server/sidequest/` (Python). The pre-port
> Rust crate paths in earlier revisions of this document have been retired —
> see `docs/adr/082-port-api-rust-to-python.md` and the translation table in
> `docs/adr/README.md`.

One complete action turn in **solo play**. The "sealed-letter" barrier stage
is architecturally present on every turn but collapses to a no-op when only
one player is in the session. See [`multiplayer-sealed-turns.md`](./multiplayer-sealed-turns.md)
for the full sealed-envelope variant.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Player
    participant UI as UI (React)<br/>App.tsx / InputBar
    participant WS as WebSocket
    participant Reader as Server Reader<br/>handle_ws_connection
    participant Disp as PlayerActionHandler<br/>(handlers/player_action.py)
    participant Narr as Narrator<br/>(claude -p subprocess)
    participant Writer as Writer Task<br/>(mpsc + broadcast)
    participant Watcher as OTEL Watcher

    Player->>UI: Types action, presses Enter
    Note over UI: handleSend(text, aside=false)<br/>optimistic: push PLAYER_ACTION into messages<br/>setCanType(false) — input locked
    UI->>WS: PLAYER_ACTION { action, aside:false }
    WS->>Reader: pydantic parse → dispatch_message
    Reader->>Disp: handle_player_action(ctx)

    Note over Disp: turn span opens<br/>turn_number = ctx.turn_manager.interaction()
    Disp->>Watcher: game / AgentSpanOpen { action, player, turn }

    Disp->>Writer: THINKING (eager, pre-LLM)
    Writer-->>WS: THINKING
    WS-->>UI: THINKING
    Note over UI: setThinking(true)

    Note over Disp: Two-pass inventory extractor<br/>classifies PREVIOUS turn's narration:<br/>Acquired / Consumed / Sold / Given / Lost / Destroyed<br/>→ mutates ctx.inventory before prompt build
    Note over Disp: Scenario between-turn processing:<br/>NPC autonomous actions, gossip spread,<br/>clue discovery, pressure & escalation beats<br/>→ appended to state_summary
    Note over Disp: build_prompt_context (state_summary)<br/>+ Monster Manual NPC/encounter injection

    rect rgba(180,180,180,0.15)
    Note over Disp: SessionRoom.TurnBarrier → no-op<br/>(no turn_barrier in solo —<br/>sealed-letter stage is skipped)
    end

    Disp->>Narr: GameService.process_action(you, context)
    Note over Narr: claude -p subprocess<br/>narrator agent (unified, ADR-067)
    Narr-->>Disp: ActionResult {<br/>narration, footnotes, location,<br/>items_gained, sfx_triggers,<br/>classified_intent, agent_name,<br/>action_rewrite, action_flags }

    Disp->>Watcher: agent / AgentSpanClose<br/>{ narration_len, intent, agent, tokens }
    Disp->>Watcher: prompt / PromptAssembled { zones, tokens }

    Note over Disp: State mutations (ctx-local):<br/>• extract_location_header → room transition<br/>• items_gained → inventory<br/>• trope tick → beats fired<br/>• turn_manager.record_interaction<br/>• scene_count increment

    Disp->>Writer: NARRATION { text, state_delta, footnotes }
    Writer-->>WS: NARRATION
    WS-->>UI: NARRATION
    Note over UI: setThinking(false)<br/>append NARRATION to messages<br/>⚠ canType NOT restored here —<br/>input stays locked (observed bug)

    Disp->>Writer: NARRATION_END
    Writer-->>WS: NARRATION_END
    WS-->>UI: NARRATION_END
    Note over UI: narrativeSegments inserts a<br/>separator — splits history from<br/>current-turn block

    Disp->>Writer: PARTY_STATUS { members[], resources }
    Writer-->>WS: PARTY_STATUS
    WS-->>UI: PARTY_STATUS
    Note over UI: setPartyMembers; fan out<br/>local slice → characterSheet, inventoryData

    opt Location changed
        Disp->>Writer: CHAPTER_MARKER { location }
        Writer-->>UI: CHAPTER_MARKER
    end
    opt New render queued
        Disp->>Writer: IMAGE { url, render_id, tier }
        Writer-->>UI: IMAGE (routed to gallery via ImageBus)
    end
    opt Item depleted
        Disp->>Writer: ITEM_DEPLETED { item_name, remaining_before }
        Writer-->>UI: ITEM_DEPLETED
    end

    Note over Disp: delta = compute_delta(before, after)<br/>broadcast_state_changes(delta) →<br/>typed messages per changed field<br/>(characters / npcs / quest_log / atmosphere / regions / tropes)
    Disp->>Writer: (typed state-change messages)
    Writer-->>UI: state-change broadcast
    Note over UI: useStateMirror processes<br/>state_delta into GameStateProvider

    Note over Disp: persistence.persist_game_state<br/>(SQLite save via asyncio.to_thread)
    Disp->>Watcher: TurnRecord (ADR-073)<br/>snapshot_before/after, patches, delta,<br/>intent, narration, tokens
```

## Code path reference

| Step | File |
|---|---|
| UI `handleSend` | `sidequest-ui/src/App.tsx` |
| WebSocket reader/writer loop | `sidequest-server/sidequest/server/websocket.py` + `websocket_session_handler.py` |
| Dispatch entry (PLAYER_ACTION) | `sidequest-server/sidequest/handlers/player_action.py` |
| `THINKING` eager send | `sidequest-server/sidequest/server/emitters.py` (via orchestrator) |
| Inventory extractor (post-port partial — see ADR-087 P1 VERIFY) | `sidequest-server/sidequest/agents/orchestrator.py` |
| Scenario between-turn | `sidequest-server/sidequest/game/scenario_state.py` |
| Barrier (no-op solo) | `sidequest-server/sidequest/server/session_room.py` (`TurnBarrier`) |
| Narrator call | `sidequest-server/sidequest/agents/narrator.py` (via `claude -p` subprocess) |
| Response build (`NARRATION` / `NARRATION_END` / `PARTY_STATUS`) | `sidequest-server/sidequest/server/narration_apply.py` |
| Delta broadcast | `sidequest-server/sidequest/game/delta.py` (`compute_delta`) + `server/emitters.py` |
| State patches | `sidequest-server/sidequest/server/dispatch/` package (per-stage handlers) |
| `TurnRecord` → OTEL | `sidequest-server/sidequest/telemetry/turn_record.py` + `validator.py` |
| Client message handler | `sidequest-ui/src/App.tsx` + `useGameSocket` |
| Narrative segment build | `sidequest-ui/src/lib/narrativeSegments.ts` |

## Solo vs. sealed-letter multiplayer

Three things collapse to no-ops when only one player is in the session:

1. **No barrier wait.** `SessionRoom.TurnBarrier` never installs for a single player.
2. **No `TurnStatus("submitted")` broadcast.** The "sealed the envelope"
   event is gated on barrier existence.
3. **No `ActionReveal`.** The reveal message is part of the barrier
   resolution path only.

So in solo, a turn is:

```
PLAYER_ACTION → THINKING → narrator → NARRATION → NARRATION_END
              → PARTY_STATUS (+ CHAPTER_MARKER / IMAGE / ITEM_DEPLETED)
              → typed state-change messages
```

(`MAP_UPDATE` was retired with the live world-map view 2026-04-28; see ADR-019 supersession + ADR-055 room-graph navigation. The cartography YAML now seeds `snap.current_region` at chargen only.)

The seal / wait / reveal ceremony only exists to keep multiplayer players
in sync and to preserve simultaneous-resolution fairness.

## Message fan-out paths

Two different fan-out paths feed the same writer task (asyncio.Queue per connection plus a shared session broadcast):

- **Per-connection queue** — targeted at one player. Used for `NARRATION`,
  `NARRATION_END`, and any response tied to the acting player. See
  `server/websocket_session_handler.py` for the reader/writer split.
- **Session broadcast** (`SessionRoom.broadcast(...)` in `server/session_room.py`) —
  scoped to players in the same genre:world session, with optional
  per-player targeting via projection-filter (`game/projection/`). Used for
  multiplayer session events including `ActionReveal` and typed state-change
  broadcasts.
- **Global watcher fan-out** (`/ws/watcher` via `server/watcher.py` + `telemetry/watcher_hub.py`) —
  separate from gameplay traffic; streams telemetry to GM Mode.

All three feed the same `ws.send_text(...)` at the bottom of the writer
`asyncio.gather(...)` loop.
