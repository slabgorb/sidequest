# ADR-074: Dice Resolution Protocol — Player-Facing Rolls via WebSocket

## Status

Proposed

## Context

SideQuest currently resolves all mechanical checks silently. When a player selects a
confrontation beat, `BeatDef.stat_check` names the relevant ability ("strength",
"dexterity") and `metric_delta` is applied directly to the encounter metric. No dice
are rolled. No randomness is visible to the player.

Playtest feedback: **players want to roll their own dice.** The tactile ritual of rolling
is a core part of the tabletop RPG experience — anticipation, agency, consequence. The
current system feels deterministic and opaque.

### Design constraints

1. **Multiplayer sealed letters** — players commit actions blind (no DC visible during
   sealed phase). Dice roll during the reveal phase, after letters open.
2. **Server authority** — the server determines outcomes. Clients render physics but
   cannot influence results. No cheating possible.
3. **Narrative integration** — the AI narrator must know the roll result and outcome
   to shape its prose. Crit success and crit fail should produce different narration tone.
4. **Not every check gets dice** — only player-facing dramatic moments use the dice
   tray. Backend perception checks, NPC rolls, and passive saves resolve silently.
5. **Dice pools** — the system must support single d20+mod and multi-die pools (4d6,
   2d10). Pool dice are thrown together in one gesture — the player does not pick up
   dice individually.

### Existing hooks

- `BeatDef.stat_check: String` — already carries the ability name on every beat
- `ConfrontationBeat` — wire format already includes `stat_check` and `metric_delta`
- `ActionReveal` — already broadcasts sealed actions to all clients with turn number
- `request_id` pattern — already used on `Image` messages for async correlation

## Decision

Add three new `GameMessage` variants for a server-authoritative dice protocol.

### New message types

**Server -> Client: `DiceRequest`**

Broadcast to all connected clients when a player-facing check is needed. Appears
after the narrator sets the scene, during the reveal phase.

```rust
DiceRequest {
    request_id: String,          // correlate request -> result
    player_id: String,           // who must throw
    character_name: String,      // display name
    dice: Vec<DieSpec>,          // [{sides: 20, count: 1}] or [{sides: 6, count: 4}]
    modifier: i32,               // stat bonus (e.g., +3 STR)
    stat: String,                // ability name from beat.stat_check
    difficulty: u32,             // DC — revealed here, NOT during sealed phase
    context: String,             // narrator flavor for the dice tray UI
}

DieSpec {
    sides: u32,                  // 4, 6, 8, 10, 12, 20, 100
    count: u32,                  // number of dice of this type
}
```

**Client -> Server: `DiceThrow`**

Sent by the rolling player only. Contains throw gesture parameters that affect
animation but not outcome.

```rust
DiceThrow {
    request_id: String,          // matches the DiceRequest
    throw_params: ThrowParams,   // direction, force, spin from flick gesture
}

ThrowParams {
    velocity: [f32; 3],          // initial velocity vector
    angular: [f32; 3],           // initial spin
    position: [f32; 2],          // release point on screen (normalized 0-1)
}
```

**Server -> Client: `DiceResult`**

Broadcast to all clients. Contains everything needed to replay identical physics
and display the outcome.

```rust
DiceResult {
    request_id: String,
    player_id: String,
    character_name: String,
    rolls: Vec<u32>,             // raw die faces, e.g., [17] or [3, 5, 2, 6]
    modifier: i32,
    total: u32,                  // sum(rolls) + modifier
    difficulty: u32,             // echo DC for UI display
    outcome: RollOutcome,        // CritSuccess | Success | Fail | CritFail
    seed: u64,                   // deterministic physics seed
    throw_params: ThrowParams,   // echo back for client replay
}

enum RollOutcome {
    CritSuccess,                 // natural max (nat 20 on d20)
    Success,                     // total >= difficulty
    Fail,                        // total < difficulty
    CritFail,                    // natural 1 on d20
}
```

### Turn flow

```
SEALED PHASE
  Player sees confrontation beats with stat_check labels.
  Player selects a beat. NO DC visible.
  Action submitted as sealed letter.

REVEAL PHASE
  ActionReveal broadcasts all sealed actions.
  For each action requiring a check:
    1. Narrator sets the scene (NarrationChunk)
    2. Server sends DiceRequest (DC revealed NOW)
    3. Player sees: "DC 18 — Dexterity +2 — you need a 16"
    4. Player flicks dice (DiceThrow)
    5. Server resolves: seed + RNG, independent of throw gesture
    6. Server broadcasts DiceResult to all clients
    7. All clients replay identical Rapier physics from seed + throw_params
    8. Narrator receives outcome, generates result narration
    9. Narration broadcast

CONTESTED ROLLS
  Two conflicting sealed letters:
    1. Narrator sets collision scene
    2. Two DiceRequests sent simultaneously
    3. Both players throw (server waits for both DiceThrow)
    4. Both DiceResults broadcast together
    5. Narrator resolves the contest
```

### Integration with existing systems

| Component | Change |
|-----------|--------|
| `BeatDef.stat_check` | Already has ability name — becomes `DiceRequest.stat` |
| `dispatch_beat_selection()` | After beat selected, pause narration, emit `DiceRequest`, await `DiceThrow`, resolve, then narrate with outcome |
| `ConfrontationBeat.metric_delta` | Scaled by outcome: crit success = 2x, success = 1x, fail = 0x, crit fail = negative |
| `ActionReveal` | Unchanged — dice are a sub-phase within reveal |
| `TurnBarrier` | Unchanged — barrier resolves action collection, dice are downstream |
| Narrator prompt | Receives `RollOutcome` to shape tone (triumph, relief, dread, comedy) |

### Server authority model

The client's throw gesture (`ThrowParams`) controls animation aesthetics — angle,
force, tumble path — but NOT the outcome. The server:

1. Receives `DiceThrow` with gesture params
2. Generates a cryptographic seed via RNG
3. Determines die face results from the seed (deterministic)
4. Computes total + modifier vs DC
5. Broadcasts `DiceResult` with seed + throw_params

All clients run identical Rapier physics from the same seed and throw params,
producing identical visual animation. The seed determines which face lands up.
The throw params determine the path to get there.

### What does NOT get dice

- Passive perception / awareness checks (backend only)
- NPC actions and saves (backend only)
- Non-confrontation exploration (backend only)
- Any check the narrator/GM resolves without player agency

The dice tray is a spotlight for dramatic moments, not a calculator for every check.

## Consequences

- New protocol surface: 3 message types + 4 supporting structs
- `dispatch_beat_selection()` becomes async (wait for throw) — already in async context
- Narrator prompt engineering must handle outcome injection
- Genre packs may define resolution systems (d20 vs 2d6 vs pool) — future extension
- OTEL spans needed: `dice.request_sent`, `dice.throw_received`, `dice.result_broadcast`

## Alternatives Considered

### Client-side resolution (rejected)
Client rolls locally, sends result to server. Trivially cheatable in multiplayer.
Violates server authority principle.

### Pre-determined animation (rejected)
Server picks result, sends pre-rendered animation. No player agency in the throw
gesture. Loses the tactile satisfaction that motivated the feature.

### Dice on every check (rejected)
Rolling for perception, saves, NPC actions. Slows the game, dilutes the dramatic
impact. Backend rolls silently for non-player checks.
