# Epic 8: Multiplayer — Turn Barrier, Party Coordination, Perception Rewriter

## Overview

Port the multiplayer coordination layer from Python to Rust. Multiple players connect
via WebSocket to a shared game session, each mapped to a character. The system collects
actions from all players, composes them into a single [PARTY ACTIONS] block for the
orchestrator, and rewrites the resulting narration per-character based on status effects
(blinded, charmed, dominated). This is the foundation for SideQuest as a group play
experience rather than a solo game.

## Background

### What Epic 2 Delivers (prerequisite)

| Component | What's Done |
|-----------|-------------|
| **Session actor** | Game session lifecycle, single-player WebSocket binding |
| **Orchestrator** | Turn loop: input -> intent -> agent -> narration -> patch -> broadcast |
| **Agent execution** | Claude CLI subprocess, prompt composition, JSON extraction |
| **State patches** | WorldStatePatch, CombatPatch, ChasePatch applied to GameSnapshot |
| **Character creation** | Character model with status effects, abilities, stats |

Epic 8 extends the single-player session actor into a multiplayer coordinator.

### Python Reference

| Python module | What it does |
|---------------|-------------|
| `multiplayer_session.py` | Player-to-character mapping, join/leave, session state |
| `turn_manager.py` | Barrier sync, action collection, timeout resolution |
| `turn_reminder.py` | Idle player notification after configurable timeout |
| `perception_rewriter.py` | Per-character narration rewriting based on status effects |

### Key ADRs

- **ADR-028: Perception Rewriter** — Characters with status effects receive altered
  narration. A charmed player sees the vampire as friendly. This is an additional
  Claude call per affected player after base narration is generated.
- **ADR-029: Guest NPC Players** — Humans can control NPC characters with limited
  agency (restricted action set, no inventory management, narrator treats them as
  semi-autonomous).

## Technical Architecture

### Session Topology

```
Player A ---> WebSocket --+
Player B ---> WebSocket --+---> MultiplayerSession ---> TurnBarrier
Player C ---> WebSocket --+         |                      |
                                    |                  all ready
                                    |                      |
                                    v                      v
                             Compose [PARTY ACTIONS] ---> Orchestrator
                                                              |
                                    +--------------------------+
                                    |
                               Narration
                                    |
                          +---------+---------+
                          v         v         v
                     Rewrite A  Rewrite B  Rewrite C
                     (charmed)  (normal)   (blinded)
                          |         |         |
                          v         v         v
                     Player A   Player B   Player C
```

### Turn Mode State Machine

```
                    +-- combat starts ---> STRUCTURED
                    |                         |
FREE_PLAY ----------+                     combat ends
  ^                 |                         |
  |                 +-- cutscene ----> CINEMATIC
  |                                       |
  +----------- scene ends ----------------+
```

- **FREE_PLAY**: Actions resolve immediately as received. No barrier. Default mode.
- **STRUCTURED**: Blind simultaneous submission. All players commit before anyone sees
  results. Used for combat and high-stakes decisions.
- **CINEMATIC**: Narrator-paced. Players receive narration and respond to prompts.
  Used for dramatic transitions and cutscenes.

### Adaptive Batching

The action collection window scales by player count to prevent slow players from
blocking the group:

| Player count | Collection window | Timeout behavior |
|-------------|-------------------|------------------|
| 1 (solo) | None (immediate) | N/A |
| 2-3 | 3 seconds | Resolve with submitted actions |
| 4+ | 5 seconds | Resolve with submitted actions |

After timeout, unsubmitted players get a default "wait/observe" action.

### Perception Rewriter Pipeline

```
Base narration (from orchestrator)
         |
         v
 For each player with active perceptual effects:
         |
    +----+----+
    |         |
 affected?  no ---> send base narration
    |
    v
 Claude call: rewrite(base_narration, character, active_effects)
    |
    v
 altered narration ---> send to affected player
```

The rewriter is the most expensive part of the multiplayer pipeline. Each affected
player requires an additional Claude CLI call. The prompt takes the base narration
and a list of active perceptual effects (blinded, charmed, dominated, hallucinating)
and produces a rewritten version filtered through that character's perception.

### Key Types

```rust
pub struct MultiplayerSession {
    pub session_id: SessionId,
    pub players: HashMap<PlayerId, CharacterId>,
    pub turn_mode: TurnMode,
    pub barrier: TurnBarrier,
    pub batching_config: BatchingConfig,
}

pub enum TurnMode {
    FreePlay,
    Structured,
    Cinematic,
}

pub struct TurnBarrier {
    pub expected: HashSet<PlayerId>,
    pub received: HashMap<PlayerId, PlayerAction>,
    pub timeout: Duration,
}

pub struct PerceptionFilter {
    pub character_id: CharacterId,
    pub effects: Vec<StatusEffect>,
}
```

## Story Dependency Graph

```
2-2 (session actor)
 |
 +---> 8-1 (MultiplayerSession — player mapping)
        |
        +---> 8-2 (turn barrier + timeout)
        |      |
        |      +---> 8-3 (adaptive batching)
        |      |
        |      +---> 8-4 (party action composition)
        |      |
        |      +---> 8-5 (turn modes)
        |      |
        |      +---> 8-9 (turn reminders)
        |
        +---> 8-6 (perception rewriter)
        |
        +---> 8-7 (guest NPC players)
        |
        +---> 8-8 (catch-up narration)
```

## Deferred (Not in This Epic)

- **Voice chat integration** — Real-time voice between players. Out of scope;
  SideQuest multiplayer is text-based with TTS narration from the daemon.
- **Party persistence** — Saving multiplayer session state for resume. Single-player
  save/load exists in Epic 2; multiplayer persistence is a future concern.
- **Spectator mode** — Read-only WebSocket connections for observers. The watcher
  from Epic 3 covers operator observation; player spectating is separate.
- **Player voting** — Democratic decision-making for party choices. The current
  model is individual actions composed into a party block, not consensus.
- **Anti-grief mechanics** — Handling adversarial players who sabotage the party.
  Trust model is out of scope for the initial port.

## Dependencies

### From Epic 2 (must complete first)
- Story 2-2: Session actor (8-1 depends on this for session lifecycle)
- Story 2-5: Orchestrator turn loop (8-4 feeds into the orchestrator)
- Story 2-3: Character creation (8-6 needs character status effects)

### From Epic 1
- Story 1-12: Structured logging (multiplayer session tracing)

## Success Criteria

During a multiplayer playtest, the system can:
1. Accept 2-4 WebSocket connections mapped to different characters in the same session
2. Collect actions from all players with barrier-sync before resolving
3. Compose a [PARTY ACTIONS] block and send it through the orchestrator
4. Adapt the collection window based on player count (3s for 2-3, 5s for 4+)
5. Switch between FREE_PLAY, STRUCTURED, and CINEMATIC turn modes mid-session
6. Rewrite narration for players with active perceptual effects (charmed player sees different text)
7. Allow a human to join as a guest NPC with restricted agency
8. Generate a catch-up summary when a player joins mid-session
