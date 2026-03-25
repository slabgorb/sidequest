---
parent: context-epic-2.md
---

# Story 2-2: Session Actor — Per-Connection Tokio Task, Connect/Create/Play State Machine, Genre Binding

## Business Context

Each WebSocket connection gets its own tokio task that owns a `Session` struct. The session
is a state machine: Connect → Create → Play. This is where the server stops being a generic
WebSocket relay and becomes a game server — it knows what genre you picked, whether you have
a character, and what phase of the game you're in.

In Python, this is all mixed into `GameServer._handle_session_event()` and
`_handle_action()` with implicit state tracked across `self._builders`, `self.orchestrator`,
and various `if` checks. The Rust version makes the state machine explicit: a `Session` enum
with typed variants, so the compiler refuses to let you process a `PLAYER_ACTION` when the
session is still in the `Create` phase.

**Python source:** `sq-2/sidequest/server/app.py` lines 450-580 (`_handle_session_event`)
**Depends on:** Story 2-1 (server bootstrap, WebSocket handler)

## Technical Approach

### What Python Does

```python
# Python: implicit state scattered across GameServer fields
async def _handle_session_event(self, player_id, msg, ws):
    event = msg.payload.get("event")
    if event == "connect":
        player_name = msg.payload.get("player_name", "")
        genre = msg.payload.get("genre") or self.genre
        world = msg.payload.get("world") or self.world
        await self._init_orchestrator()  # lazy, might already exist
        # check if player has character...
        # check if player has in-progress builder...
        # otherwise start creation...
```

The problems:
- No compile-time guarantee that `_init_orchestrator()` was called before accessing `self.orchestrator`
- Builder state (`self._builders`) is a dict on the server, not owned by the session
- Genre/world come from either CLI args or the connect message, with fallback logic
- Nothing prevents sending PLAYER_ACTION before connect — it just crashes at runtime

### What Rust Does Differently

**Explicit state machine with typed phases:**

```rust
enum Session {
    /// Waiting for SESSION_EVENT { event: "connect" }
    AwaitingConnect,

    /// Genre bound, character creation in progress
    Creating {
        genre_pack: Arc<GenrePack>,
        builder: CharacterBuilder,
        save_dir: PathBuf,
    },

    /// Game is active, player has a character
    Playing {
        genre_pack: Arc<GenrePack>,
        game_state: GameState,
        // agent handles, orchestrator reference
    },
}
```

**Why this matters:**
- You literally cannot access `game_state` when the session is in `Creating` — it doesn't exist in that variant. The compiler enforces it.
- You cannot access `builder` when the session is in `Playing` — the builder was consumed when the character was finalized.
- Each transition is an explicit move: `Session::AwaitingConnect` → `Session::Creating { ... }` → `Session::Playing { ... }`.
- Python's "check if orchestrator exists, check if builder exists, check if character exists" becomes a single `match session { ... }` with exhaustive arms.

**Genre binding becomes a typed transition:**

```rust
impl Session {
    fn connect(
        self,
        genre_pack: Arc<GenrePack>,
        existing_save: Option<GameState>,
    ) -> Session {
        match existing_save {
            Some(state) => Session::Playing { genre_pack, game_state: state, .. },
            None => Session::Creating { genre_pack, builder: CharacterBuilder::new(&genre_pack), .. },
        }
    }
}
```

Python's `_init_orchestrator()` does 12 things (genre load, agent spawn, prompt compose,
media init, voice assign, etc.). The Rust version separates:
- Genre loading → happens once, cached in `Arc<GenrePack>` via `GenreCache` (already built in sidequest-genre)
- Agent spawning → deferred to story 2-5/2-6 (orchestrator)
- Media init → deferred entirely (not in this epic)

### Session Connect Flow

```
Client: SESSION_EVENT { event: "connect", player_name: "Keith", genre: "mutant_wasteland", world: "flickering_reach" }

Server:
1. Load genre pack: GenreCache::get_or_load(genre, genre_packs_path) → Arc<GenrePack>
2. Resolve save_dir: ~/.sidequest/saves/{genre}/{world}/
3. Check for existing save: save_dir/state.json exists?
   - Yes → load GameState, check if player has character
     - Has character → transition to Playing, send SESSION_EVENT { event: "ready", initial_state }
     - No character → transition to Creating
   - No → transition to Creating
4. Send SESSION_EVENT { event: "connected", has_character: bool }
5. If Creating → send first CHARACTER_CREATION scene (story 2-3 handles the flow)

Where Python also:
- Evicts stale connections with same player_name (keep, but move to AppState)
- Sends theme_css (defer — nice-to-have, not core loop)
- Reads starting_location from world.yaml (keep)
```

### Message Dispatch Per Phase

| Session Phase | Allowed Messages | Rejected Messages |
|---|---|---|
| `AwaitingConnect` | SESSION_EVENT (connect only) | Everything else → ERROR |
| `Creating` | CHARACTER_CREATION, SESSION_EVENT (disconnect) | PLAYER_ACTION → ERROR "character creation in progress" |
| `Playing` | PLAYER_ACTION, SESSION_EVENT | CHARACTER_CREATION → ERROR "already have character" |

Python doesn't enforce this — it checks at runtime with `if player_id in self._builders`.
Rust enforces it at the type level: the `match` on `Session` determines what's valid.

### Stale Connection Eviction

Python evicts connections when the same player_name reconnects:
```python
stale_ids = [pid for pid, name in self.player_names.items()
             if name == player_name and pid != player_id]
```

Rust does this in `AppState`:
```rust
impl AppState {
    fn evict_stale(&self, player_name: &str, current_id: &PlayerId) {
        self.connections.retain(|id, _| {
            id == current_id || self.player_names.get(id).map_or(true, |n| n != player_name)
        });
    }
}
```

### Starting Location

Python reads `starting_location` from `genre_packs/{genre}/worlds/{world}/world.yaml`.
This is already available through the loaded `GenrePack` — the genre loader (story 1-4)
loads world data. Access it as `genre_pack.worlds[world_slug].starting_location`.

If the world has no starting_location, that's a genre pack validation error, not a runtime
panic. The Rust version should return a typed error, not `RuntimeError`.

## Scope Boundaries

**In scope:**
- `Session` enum with `AwaitingConnect`, `Creating`, `Playing` variants
- Connect handler: genre load, save check, state machine transition
- Per-phase message dispatch (type-safe routing based on session state)
- Stale connection eviction
- Starting location from genre pack world data
- SESSION_EVENT response messages (connected, ready, initial_state)
- Session owned by its tokio task — no shared mutable state

**Out of scope:**
- Character creation logic (story 2-3)
- Game turn processing (story 2-5)
- SQLite persistence (story 2-4 — for now, use JSON file I/O as interim)
- Theme CSS generation (deferred)
- Voice/audio binary frames (deferred)
- Multiplayer shared state (single-player first)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Connect flow | SESSION_EVENT connect → genre loaded → SESSION_EVENT connected response |
| New player | No existing save → session transitions to Creating phase |
| Returning player | Existing save with character → session transitions to Playing, sends initial_state |
| Phase gating | PLAYER_ACTION during Creating phase → ERROR message, not crash |
| Stale eviction | Same player_name reconnects → old connection closed cleanly |
| Starting location | Game state has location set from genre pack world data |
| Genre cache | Two connections to same genre share the same `Arc<GenrePack>` |
| Error on bad genre | Connect with non-existent genre → ERROR message with explanation |

## Type-System Wins Over Python

1. **Session phase is a type, not implicit state.** No more "is the orchestrator initialized? is there a builder? does the player have a character?" — it's one `match`.
2. **Genre binding is a transition, not a side effect.** `Session::connect()` returns a new variant — you can't forget to bind the genre.
3. **Impossible states are unrepresentable.** You can't have a `builder` and a `game_state` at the same time — they're in different enum variants.
4. **Messages are routed by phase at compile time.** The match arms for `Creating` don't have access to `game_state` — you can't accidentally reference it.
