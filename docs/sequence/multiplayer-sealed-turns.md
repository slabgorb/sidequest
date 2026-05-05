# Multiplayer Sealed Letter Turns

> **Last updated:** 2026-05-05 (post-port; ADR-082)
>
> Simultaneous action submission with claim-based narrator resolution.
> Players submit privately behind a barrier; one narrator call resolves all actions.
>
> Module paths reference `sidequest-server/sidequest/` (Python). The pre-port
> Rust crate paths in earlier revisions of this document have been retired —
> see `docs/adr/082-port-api-rust-to-python.md`.

## Turn Mode Activation

```mermaid
stateDiagram-v2
    [*] --> FreePlay : solo session
    FreePlay --> Structured : 2nd player joins
    FreePlay --> Cinematic : cutscene starts
    Structured --> FreePlay : player leaves (count ≤ 1)
    Structured --> FreePlay : combat ends
    Cinematic --> FreePlay : scene ends
```

Barrier is only active in **Structured** and **Cinematic** modes. FreePlay resolves actions immediately (no barrier).

## Sealed Turn Sequence

```mermaid
sequenceDiagram
    participant A as Player A (UI)
    participant B as Player B (UI)
    participant S as Server (server/session_room.py)
    participant TB as TurnBarrier
    participant MS as MultiplayerSession
    participant SR as SealedRoundContext
    participant N as Narrator (Claude)
    participant SS as SessionSync

    Note over A,B: Phase 1 — Concurrent Action Submission

    par Player A submits
        A->>S: PLAYER_ACTION { action, player_id }
        S->>TB: submit_action(player_a, "I attack the goblin")
        TB->>MS: record action
        S-->>A: TurnStatus "submitted"
        S-->>B: TurnStatus "submitted" (broadcast)
        S->>TB: wait_for_turn() [BLOCKS]
    and Player B submits
        B->>S: PLAYER_ACTION { action, player_id }
        S->>TB: submit_action(player_b, "I cast shield on Alice")
        TB->>MS: record action
        S-->>B: TurnStatus "submitted"
        Note over TB: barrier_met = true
        TB->>TB: notify.notify_one()
    end

    Note over TB: Phase 2 — Claim Election

    TB->>TB: resolve(timed_out: false)
    Note over TB: Atomic lock on last_claim_turn<br/>First task to arrive claims resolution

    alt Claiming handler (Player A's task)
        TB-->>S: TurnBarrierResult { claimed: true, named_actions }
    else Non-claiming handler (Player B's task)
        TB-->>S: TurnBarrierResult { claimed: false }
        Note over S: Enters polling loop<br/>100ms intervals, 30s timeout
    end

    Note over S,N: Phase 3 — Narrator Call (claiming handler only)

    S->>SR: build(named_actions, encounter_type, initiative_rules)
    SR-->>S: formatted prompt section

    S-->>A: ActionReveal { all player actions }
    S-->>B: ActionReveal { all player actions }

    S->>N: claude -p (narrator)<br/>state_summary includes sealed round context
    N-->>S: narration + sidecar tool results

    Note over S,SS: Phase 4 — State Mutation & Broadcast

    S->>TB: store_resolution_narration(narration)
    Note over S: Non-claimer retrieves narration via polling

    S->>SS: sync_back_to_shared_session()

    par Per-player delivery
        SS-->>A: NARRATION (possibly perception-rewritten)
        SS-->>A: NARRATION_END
    and
        SS-->>B: NARRATION (possibly perception-rewritten)
        SS-->>B: NARRATION_END
    end

    SS-->>A: TurnStatus "resolved"
    SS-->>B: TurnStatus "resolved"
```

## Adaptive Timeout

```mermaid
flowchart LR
    subgraph Timeout Tiers
        T1["< 4 players<br/>3 seconds"]
        T2["4+ players<br/>5 seconds"]
        T3["Disabled<br/>infinite wait"]
    end

    T1 -->|player joins| T2
    T2 -->|player leaves| T1
```

When timeout fires, missing players get auto-resolved with "hesitates" actions (mode-aware: "remains silent" for Cinematic).

## Non-Claimer Polling

```mermaid
sequenceDiagram
    participant NC as Non-Claiming Handler
    participant TB as TurnBarrier
    participant CL as Claiming Handler

    CL->>TB: store_resolution_narration(text)

    loop Every 100ms (up to 30s)
        NC->>TB: get_resolution_narration()
        alt narration available
            TB-->>NC: Some(narration)
            NC-->>NC: send Narration + NarrationEnd to player
            Note over NC: Early exit — skip narrator call
        else not yet
            TB-->>NC: None
        end
    end
```

## Perception Rewriting

After resolution, each player may receive a different version of the narration based on active `PerceptualEffect`s (blinded, charmed, hallucinating, etc.). This is now an in-narrator subsystem (ADR-067 unified narrator) — the standalone resonator agent of the pre-port architecture was collapsed into the unified narrator.

```mermaid
flowchart TD
    N[Base Narration] --> CHECK{perception_filters\nexist for player?}
    CHECK -->|No| SEND[Send base narration]
    CHECK -->|Yes| REWRITE[agents.perception_rewriter\nADR-028]
    REWRITE -->|Success| FILTERED[Send rewritten narration]
    REWRITE -->|Failure| FALLBACK[Send base narration\nwith effect annotation]
```

## Key Files

| File | Purpose |
|------|---------|
| `sidequest-server/sidequest/server/session_room.py` | `SessionRoom`, `TurnBarrier`, claim election, adaptive timeout |
| `sidequest-server/sidequest/game/session.py` | Per-session state, `TurnMode` (FreePlay / Structured / Cinematic) |
| `sidequest-server/sidequest/game/shared_world_delta.py` | Shared-world delta handshake (story 45-1) |
| `sidequest-server/sidequest/server/session_handler.py` | Multiplayer dispatch path |
| `sidequest-server/sidequest/handlers/player_action.py` | PLAYER_ACTION inbound handler |
| `sidequest-server/sidequest/handlers/action_reveal.py` | Sealed-letter reveal dispatch |
| `sidequest-server/sidequest/server/dispatch/sealed_letter.py` | Phase-5 sealed-letter dispatch (used by dogfight + magic confrontation outcomes) |
| `sidequest-server/sidequest/agents/perception_rewriter.py` | Per-player narration variants (ADR-028) |
| `sidequest-server/sidequest/game/projection_filter.py` + `game/projection/` | Per-player view computation |

## OTEL Events

| Event | When |
|-------|------|
| `sealed_round.claim_election` | Claim resolved (claimed, timed_out, missing_players) |
| `sealed_round.effective_action` | Combined action text sent to narrator |
| `sealed_round.poll_result` | Non-claimer retrieval (success/timeout, attempts) |
| `barrier.resolved` | Barrier complete (player_count, submitted, timed_out) |
| `perception.rewrite` | Per-player narration variant generated |
| `multiplayer.narration_broadcast` | Final narration sent (observer_count, text_len) |
