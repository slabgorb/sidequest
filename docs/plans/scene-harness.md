# Plan: Scene Harness (verified)

**Status:** Ready to execute. All wiring verified against code.

**Goal:** `just scene poker` / `just scene dogfight` / `just scene negotiation` drops a running session into an active encounter in under 10 seconds, bypassing the narrative runway. Collapses encounter-iteration loop from ~10 min to ~10 sec.

**Why now:** Every encounter-adjacent bug currently requires playing through chargen + intro turns to reach an encounter. The two-phase dice fix (next plan) specifically needs fast repeatable access to an active encounter with beats available. Scene harness unblocks it.

**Authority:** Supersedes ADR-069 schema in favor of a simpler "reference a ConfrontationDef by type" model, since verification showed beats must come from the genre pack, not inline. ADR-069's save-file-via-SqliteStore approach is kept intact.

---

## Verified facts (source of truth — not guesses)

All 19 items from the verification pass have been resolved. Summary:

### What exists and works as-is (GREEN)

- `SqliteStore::save()` serializes `StructuredEncounter` unconditionally via `GameSnapshot` serde round-trip. `persistence.rs:295-310`.
- `SqliteStore` writes via `INSERT OR REPLACE` — fixture reloads overwrite cleanly.
- `AppState.genre_cache` is shared across routes — the dev route reuses the same loaded genre packs as normal dispatch.
- Narrator session is reset on every connect via `state.game_service().reset_narrator_session_for_connect()`. No warm-state bootstrap needed. `dispatch/connect.rs:68`.
- Dice overlay state is session-scoped in `useState(null)` — fresh on session boot. `App.tsx:241-242`.
- `TurnManager` fields that persist: `round`, `interaction`, `phase`, `player_count`. Only `interaction` needs fixture-level control. `turn.rs:51-83`.
- GM panel is span-agnostic — all `WatcherEvent` items with `StateTransition` type render. No allowlist to update.
- Three distinct beat types exist with clear separation: `BeatDef` (genre-pack YAML source), in-memory `StructuredEncounter.beats`, and `ConfrontationBeat` (wire format to UI). Conversion is already wired in `response.rs:328-341`.

### What needs adaptation (YELLOW)

- **Single metric per encounter.** `StructuredEncounter` has `metric: EncounterMetric` (singular), not a vec. `metric_delta: i32` per beat, not a keyed array. Thresholds live on the metric (`threshold_high` / `threshold_low`), not on a separate `resolution:` block. **Impact:** fixture doesn't specify metrics at all — they come from the ConfrontationDef.
- **UI has no URL-based session join.** `App.tsx:37-63` uses `sessionStorage["sidequest-session"] = { playerName, genre, world }`. No query-param parsing for session_id. **Fix:** add query-param handling to ConnectScreen (scoped below).
- **WebSocket URL is `/ws`, no query params.** The UI connects to `ws://${window.location.host}/ws` from `useGameSocket.ts`. Session identification is via sessionStorage values passed in the Connect message.
- **`CharacterBuilder` is the only public construction path.** Multi-step, requires human responses. **Fix:** hydrate `Character` via serde deserialization from the fixture YAML, using the existing `GameSnapshot` serde round-trip. No new game-crate API.
- **`sidequest-telemetry` exposes a builder, not helpers.** Use `WatcherEventBuilder::new("scene_harness", StateTransition).field(...).send()` inline in the dev route.

### What is broken and must be fixed as part of this work (RED)

- **`dispatch_connect()` does not emit `CONFRONTATION` on restore.** When a save with `snapshot.encounter.is_some()` is loaded, no encounter message is sent to the joining client. The UI shows nothing until the first turn completes. This is a real wiring gap — not just a scene harness problem, but a latent bug in save restore generally. **Fix:** emit `CONFRONTATION` from `dispatch_connect.rs` after snapshot load if an encounter is present. 3-5 lines.
- **No existing session creation API.** Sessions are created implicitly by `dispatch_connect` when chargen completes or a save is loaded. **Fix:** dev route explicitly calls `persistence().save()` to write the fixture save to the standard path, then the normal `dispatch_connect` restore path picks it up when the UI connects.
- **Beats cannot be hand-authored in fixtures.** `encounter_gate.rs:79` calls `find_confrontation_def(confrontation_defs, incoming_type)`. If the type doesn't resolve to a ConfrontationDef in the loaded genre pack, the gate emits `encounter.creation_failed_unknown_type` and refuses to create the encounter. **Fix:** fixture specifies `encounter.type: poker` and relies on the existing `from_confrontation_def()` conversion. Fixture content is drastically reduced.

### Three-tool verification of confrontation type availability

All three requested scenes resolve to existing `ConfrontationDef` entries in genre-pack `rules.yaml`:

| Scene | Genre | World (verified) | ConfrontationDef type |
|---|---|---|---|
| poker | `spaghetti_western` | `dust_and_lead` | `- type: poker` (line in rules.yaml) |
| dogfight | `space_opera` | `aureate_span` | `- type: dogfight` |
| negotiation | `pulp_noir` | `annees_folles` | `- type: negotiation` |

**Zero new content authoring required.** The genre packs already ship these.

---

## Success criteria (all must be green)

1. `just scene poker` boots the API server with `DEV_SCENES=1`, hits the dev route, opens the UI at `http://localhost:5173?scene=poker`, and the EncounterSheet is visible with poker beats within 10 seconds. Same for `dogfight` and `negotiation`.
2. An integration test in `sidequest-api/crates/sidequest-server/tests/scene_harness.rs` loads `scenarios/fixtures/poker.yaml`, hydrates into a `GameSnapshot`, saves via `SqliteStore`, creates an in-process test server, connects a WebSocket client, and asserts that the first `CONFRONTATION` message arrives with non-empty beats within 2 seconds. This test is the **wiring gate** — it must exist and pass before the story ships.
3. Running `sidequest-fixture load poker` a second time against the same save path overwrites without error.
4. OTEL event `scene.loaded { fixture_name, genre, world, has_encounter }` appears in the GM panel when a scene boots.
5. The dev route is only mounted when `DEV_SCENES=1` is set in the server environment. Without the env var, `POST /dev/scene/poker` returns 404 (route not registered, not a reject).
6. Code review checklist (replacing `sq wire-it audit`):
   - `sidequest-fixture` crate is listed in `sidequest-api/Cargo.toml` workspace members.
   - The dev route module is conditionally mounted in `sidequest-server/src/lib.rs`.
   - `scenarios/fixtures/poker.yaml`, `dogfight.yaml`, `negotiation.yaml` exist and are loadable.
   - `dispatch_connect` emits `CONFRONTATION` on restore — verified with a save-and-reload test.
   - The integration test in item 2 is called from `sidequest-server` test suite, not a sibling crate.
7. **`just scene poker` works end-to-end from a cold start with no manual sessionStorage manipulation, no UI mouse-clicking through ConnectScreen, and no server restart between scenes.**

---

## Schema (verified)

Fixture file: `scenarios/fixtures/<name>.yaml`

```yaml
name: Poker — High Stakes
genre: spaghetti_western      # must be a loaded genre pack
world: dust_and_lead          # must be a world slug under that pack
description: Four-hand poker with Black Bart. Grit vs grit.

# UI session identity — dev route returns these to the UI query-param reader
player_name: fixture-poker    # unique per fixture; used as save path segment

character:
  # Serde-compatible with Character struct. Fields must match what
  # GameSnapshot.characters[0] expects. Unknown fields rejected.
  name: "Dusty McGraw"
  class: Gambler
  race: Frontier Born
  level: 3
  hp: 15
  max_hp: 20
  ac: 12
  stats:
    GRIT: 12
    DRAW: 14
    NERVE: 16
    CUNNING: 13
    PRESENCE: 15
    LUCK: 10
  inventory:
    - { name: "Deck of Marked Cards" }
    - { name: "Peacemaker Revolver", equipped: true }
    - { name: "Flask of Rotgut" }
  resources:
    luck: 3.0

location: "The Whitesand Saloon, Dust-and-Lead County"
turn: 8

npcs:
  - name: "Black Bart"
    role: outlaw
    disposition: hostile
  - name: "Miss Clara"
    role: saloon_owner
    disposition: neutral

encounter:
  type: poker                 # must match a ConfrontationDef.type in spaghetti_western/rules.yaml
  # No beats, metrics, or resolution defined here.
  # Hydration calls find_confrontation_def(...) + from_confrontation_def(...)
  # from sidequest-game::encounter. All beat/metric data comes from the genre pack.
```

**Hydration rules:**

1. `genre` and `world` are required. Hydration errors loudly (`FixtureError::UnknownGenre` / `UnknownWorld`) if either slug is absent.
2. `character:` is serialized to JSON and deserialized via `serde_json::from_value::<Character>(...)`. Field names and types must match `Character`. `#[serde(deny_unknown_fields)]` at the top of the fixture struct (not on Character — Character's own serde rules apply).
3. `npcs:` produces `Npc` entries with `NpcCore { name, role }` and the specified disposition. OCEAN profile uses defaults.
4. `encounter.type` is resolved via `find_confrontation_def(&genre_pack.confrontations, &fixture.encounter.type)`. If `None`, hydration returns `FixtureError::UnknownConfrontationType { name, genre }`. If `Some(def)`, `StructuredEncounter::from_confrontation_def(&def)` produces the encounter.
5. `turn:` populates `turn_manager.interaction`. `turn_manager.phase` defaults to `TurnPhase::InputCollection`. `round` is derived from `interaction` using existing logic.
6. All unspecified `GameSnapshot` fields use `Default::default()`.

**No silent fallbacks.** Any missing genre, world, or confrontation type is a hard error with a clear message. Any unknown field at the top level of the fixture is a hard error.

---

## File-by-file edits

### New crate: `sidequest-api/crates/sidequest-fixture/`

**`Cargo.toml`:**
```toml
[package]
name = "sidequest-fixture"
version.workspace = true
edition.workspace = true

[dependencies]
sidequest-game = { path = "../sidequest-game" }
sidequest-genre = { path = "../sidequest-genre" }
serde = { workspace = true, features = ["derive"] }
serde_yaml = { workspace = true }
serde_json = { workspace = true }
clap = { version = "4", features = ["derive"] }
anyhow = "1"
thiserror = { workspace = true }

[[bin]]
name = "sidequest-fixture"
path = "src/bin/sidequest-fixture.rs"
```

**`src/lib.rs`:**
```rust
pub mod schema;
pub mod hydrate;
pub mod error;

pub use error::FixtureError;
pub use schema::Fixture;
pub use hydrate::{load_fixture, hydrate_fixture};
```

**`src/schema.rs`** (~80 LOC):
- `Fixture` with `#[serde(deny_unknown_fields)]` at top level
- Fields: `name`, `genre`, `world`, `description`, `player_name`, `character: serde_json::Value`, `location`, `turn`, `npcs: Vec<FixtureNpc>`, `encounter: FixtureEncounter`, `resources: Option<HashMap<String, f64>>`
- `FixtureNpc { name, role, disposition }`
- `FixtureEncounter { type: String }` — just the type key, nothing else

**`src/hydrate.rs`** (~150 LOC):
- `load_fixture(path: &Path) -> Result<Fixture, FixtureError>` — reads YAML via serde_yaml
- `hydrate_fixture(fixture: &Fixture, genre_pack: &GenrePack) -> Result<GameSnapshot, FixtureError>`:
  1. Validate world slug exists in pack
  2. `character: Character = serde_json::from_value(fixture.character.clone())?`
  3. Resolve `encounter.type` via `find_confrontation_def`
  4. `StructuredEncounter::from_confrontation_def(&def)`
  5. Build `GameSnapshot { characters: vec![character], encounter: Some(enc), npcs: ..., turn_manager: ..., ..Default::default() }`

**`src/error.rs`** (~30 LOC):
```rust
#[derive(Debug, thiserror::Error)]
pub enum FixtureError {
    #[error("fixture file not found: {0}")]
    NotFound(PathBuf),
    #[error("YAML parse error: {0}")]
    Parse(#[from] serde_yaml::Error),
    #[error("character deserialization: {0}")]
    Character(#[from] serde_json::Error),
    #[error("unknown genre '{0}' — not loaded in genre pack cache")]
    UnknownGenre(String),
    #[error("unknown world '{world}' for genre '{genre}'")]
    UnknownWorld { genre: String, world: String },
    #[error("unknown confrontation type '{type_}' for genre '{genre}' — check rules.yaml")]
    UnknownConfrontationType { genre: String, type_: String },
    #[error("persistence error: {0}")]
    Persistence(#[from] sidequest_game::persistence::PersistError),
}
```

**`src/bin/sidequest-fixture.rs`** (~100 LOC):
- Clap CLI with `load <name>`, `list`, `dump <name>` subcommands
- `load`: reads `scenarios/fixtures/<name>.yaml` (or full path), hydrates, writes via `SqliteStore::new(path_for(genre, world, player_name))` + `.save(&snapshot)`, prints save path + summary
- `list`: scans `scenarios/fixtures/*.yaml`, prints name + description
- `dump`: hydrates and prints resulting `GameSnapshot` as JSON for debugging

### Workspace registration

**`sidequest-api/Cargo.toml`** — add `"crates/sidequest-fixture"` to `[workspace] members`. One line.

### Dev route: `sidequest-api/crates/sidequest-server/src/dispatch/dev_scenes.rs`

**New file** (~80 LOC).

```rust
// Only compiled and mounted if DEV_SCENES=1 is set at server startup.
// GET  /dev/scene/:name → returns { player_name, genre, world, ws_url } for the UI
// POST /dev/scene/:name → loads fixture, writes save, returns same payload

pub async fn get_scene_metadata(
    Path(name): Path<String>,
    State(state): State<AppState>,
) -> Result<Json<SceneMetadata>, ScenesError> {
    let fixture = sidequest_fixture::load_fixture(&fixture_path(&name))?;
    // no write — just read the YAML and echo coordinates
    Ok(Json(SceneMetadata {
        player_name: fixture.player_name,
        genre: fixture.genre,
        world: fixture.world,
        ws_url: format!("ws://{}/ws", state.config.http_bind_address()),
    }))
}

pub async fn load_scene(
    Path(name): Path<String>,
    State(state): State<AppState>,
) -> Result<Json<SceneMetadata>, ScenesError> {
    let fixture = sidequest_fixture::load_fixture(&fixture_path(&name))?;
    let pack = state.genre_cache().get_or_load(&fixture.genre)?;
    let snapshot = sidequest_fixture::hydrate_fixture(&fixture, &pack)?;

    let store = SqliteStore::new(&save_path(&fixture.genre, &fixture.world, &fixture.player_name))?;
    store.save(&snapshot)?;

    WatcherEventBuilder::new("scene_harness", WatcherEventType::StateTransition)
        .field("event", "scene.loaded")
        .field("fixture_name", &name)
        .field("genre", &fixture.genre)
        .field("world", &fixture.world)
        .field("has_encounter", snapshot.encounter.is_some())
        .send();

    Ok(Json(SceneMetadata { ... }))
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/scene/:name", get(get_scene_metadata).post(load_scene))
}
```

### Server mount: `sidequest-api/crates/sidequest-server/src/lib.rs`

Add near the end of router construction:

```rust
if std::env::var("DEV_SCENES").ok().as_deref() == Some("1") {
    tracing::warn!("DEV_SCENES=1 — /dev/scene/* routes are live. DO NOT enable in production.");
    app = app.nest("/dev", crate::dispatch::dev_scenes::router());
}
```

### RED FIX #1: emit `CONFRONTATION` on session restore

**`sidequest-api/crates/sidequest-server/src/dispatch/connect.rs`** — after the snapshot load path (where `state.persistence().load(...)` returns `Some(saved_session)`), add:

```rust
if let Some(ref enc) = ctx.snapshot.encounter {
    let confrontation_msg = build_confrontation_message(enc, &ctx.genre_pack)?;
    outgoing.push(GameMessage::Confrontation(confrontation_msg));
    tracing::info!(
        encounter_type = %enc.confrontation_type,
        beats = enc.beats.len(),
        "emitting CONFRONTATION on session restore"
    );
}
```

`build_confrontation_message` already exists in `response.rs` — factor it to a pub function or duplicate the 3-4 lines inline. Prefer factoring: one source of truth for CONFRONTATION construction.

**Wiring test:** `sidequest-server/tests/dispatch_connect_restore.rs` — new test that saves a snapshot with an active encounter, reloads, connects a WS client, asserts CONFRONTATION message in the first 500ms of messages.

This is a latent bug fix beyond scene harness. It's in scope because:
- It blocks the scene harness success criteria #1
- It's incidental to the current story
- Per Keith's feedback rules: fixes during cleanup work are never "scope creep"

### RED FIX #2: UI scene query-param handler

**`sidequest-ui/src/screens/ConnectScreen.tsx`** (or wherever session bootstrap happens) — add at the top of the component mount:

```tsx
useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  const sceneName = params.get('scene');
  if (!sceneName) return;

  // Resolve scene coordinates from the dev route
  fetch(`/dev/scene/${sceneName}`)
    .then(r => {
      if (!r.ok) throw new Error(`scene ${sceneName} not found`);
      return r.json();
    })
    .then(({ player_name, genre, world }) => {
      sessionStorage.setItem('sidequest-session', JSON.stringify({
        playerName: player_name,
        genre,
        world,
      }));
      // Trigger auto-connect — reuse existing restore path
      onAutoConnect({ playerName: player_name, genre, world });
    })
    .catch(err => {
      console.error('scene harness load failed:', err);
      // Fail loud — do NOT silently fall back to manual ConnectScreen
      alert(`Scene harness failed: ${err.message}`);
    });
}, []);
```

`onAutoConnect` is whatever function already handles returning-player session restore. If it doesn't exist as a clean entry point, factor one out — do not duplicate the connect logic.

### Fixtures (orchestrator repo)

**`scenarios/fixtures/poker.yaml`** — as shown in Schema section above.

**`scenarios/fixtures/dogfight.yaml`:**
```yaml
name: Dogfight — Aureate Intercept
genre: space_opera
world: aureate_span
description: Two-ship intercept on a contested lane.
player_name: fixture-dogfight
character:
  name: "Nyx Corvane"
  class: Pilot                  # verify class name exists in space_opera rules.yaml
  race: Human                   # verify
  level: 3
  hp: 14
  max_hp: 18
  # ...abilities and stats matching space_opera's ability_score_names
location: "Lane 7, approach vector Delta"
turn: 4
npcs:
  - name: "Kess Vandor"
    role: enemy_pilot
    disposition: hostile
encounter:
  type: dogfight
```

**`scenarios/fixtures/negotiation.yaml`:**
```yaml
name: Negotiation — Mob Meeting
genre: pulp_noir
world: annees_folles
description: Backroom meet with the syndicate boss.
player_name: fixture-negotiation
character:
  name: "Jack Halloran"
  class: Gumshoe                # verify
  # ...
location: "The Back Room at Mickey's"
turn: 6
npcs:
  - name: "Salvatore 'The Pipe' Moretti"
    role: mob_boss
    disposition: hostile
encounter:
  type: negotiation
```

**Verification step before authoring character blocks:** For each of the three genres, read `rules.yaml` to get valid `allowed_classes`, `allowed_races`, and `ability_score_names`. Use real values, not placeholders. If any class/race name is wrong, serde deserialization fails loudly — good, catches the mistake at fixture-load time.

### Justfile recipes (orchestrator)

**`justfile`** — add:
```
scene name:
    #!/usr/bin/env bash
    set -euo pipefail
    pkill -f sidequest-server || true
    sleep 1
    (cd sidequest-api && DEV_SCENES=1 cargo run --release --bin sidequest-server) &
    SERVER_PID=$!
    trap "kill $SERVER_PID 2>/dev/null || true" EXIT
    # Wait for server to be ready
    until curl -sf http://localhost:8080/health >/dev/null 2>&1; do sleep 0.3; done
    # Trigger fixture load
    curl -sSf -X POST http://localhost:8080/dev/scene/{{name}} | jq
    # Open UI with scene param
    open "http://localhost:5173?scene={{name}}"
    wait $SERVER_PID

scene-list:
    @ls scenarios/fixtures/*.yaml 2>/dev/null | xargs -n1 basename | sed 's/\.yaml$//' || echo "no fixtures"
```

Note: this assumes the UI dev server is already running on 5173. Scene harness doesn't auto-boot the UI — that's a separate tmux pane, and auto-booting it would fight with existing dev workflows.

### Integration test

**`sidequest-api/crates/sidequest-server/tests/scene_harness.rs`:**

```rust
#[tokio::test]
async fn scene_harness_poker_end_to_end() {
    let tmp = tempdir().unwrap();
    std::env::set_var("SIDEQUEST_HOME", tmp.path());

    // 1. Load fixture
    let fixture = sidequest_fixture::load_fixture(
        Path::new("../../../scenarios/fixtures/poker.yaml")
    ).expect("fixture loads");

    // 2. Hydrate against real spaghetti_western genre pack
    let pack = load_test_genre_pack("spaghetti_western");
    let snapshot = sidequest_fixture::hydrate_fixture(&fixture, &pack).unwrap();
    assert!(snapshot.encounter.is_some());
    let enc = snapshot.encounter.as_ref().unwrap();
    assert!(!enc.beats.is_empty(), "poker ConfrontationDef must define beats");

    // 3. Save via SqliteStore
    let store = SqliteStore::new(&save_path_for(&fixture)).unwrap();
    store.save(&snapshot).unwrap();

    // 4. Boot in-process server with DEV_SCENES=1
    let app = build_test_app_with_dev_scenes();
    let server = TestServer::new(app).unwrap();

    // 5. Connect WebSocket with matching player/genre/world
    let (ws, _) = server.ws("/ws").await;
    ws.send_connect("fixture-poker", "spaghetti_western", "dust_and_lead").await;

    // 6. Assert CONFRONTATION arrives within 2s
    let msg = ws.recv_matching(
        |m| matches!(m, GameMessage::Confrontation(_)),
        Duration::from_secs(2),
    ).await.expect("CONFRONTATION on restore");

    if let GameMessage::Confrontation(c) = msg {
        assert_eq!(c.type_, "poker");
        assert!(!c.beats.is_empty());
        assert_ne!(c.active, Some(false));  // must be active on arrival
    }
}
```

**This test is the wiring gate.** If it does not exist or does not pass, the story is not done.

---

## Anti-scope (explicit, non-negotiable)

- **No fixture editor UI.** YAML + reload is the iteration loop.
- **No auto-generated fixtures from save files.** Hand-authored.
- **No multiplayer.** `party[1..]` is not even in the schema. Single character only.
- **No scene archetype registry / abstraction.** `encounter.type` is a literal string matching a ConfrontationDef key. No layering, no generic "scene archetype" concept on top. The genre pack is the registry.
- **No character builder modification.** Hydration uses direct serde deserialization. Do not touch `CharacterBuilder`.
- **No production menu entry.** `DEV_SCENES=1` gates the dev route entirely. Without the env var, the route is not registered.
- **No cleanup of ADR-069.** Do not update, supersede, or status-flip the old ADR during this work. ADR hygiene is a separate concern, and this plan is the authoritative source of truth for what ships.
- **No two-phase dice fixes in this story.** The current broken dice flow will still be broken when scene harness ships. That's fine — scene harness is the *tool* used to fix dice next. Do not conflate them.

---

## Open dependencies (verified, not deferrable)

These are single-grep resolutions to be done as the first step of execution, NOT deferred to later:

1. **Read `spaghetti_western/rules.yaml` in full** — confirm valid `allowed_classes`, `allowed_races`, `ability_score_names`, `character` schema expectations. Author `poker.yaml` character block against these exact values.
2. **Read `space_opera/rules.yaml` in full** — same, for dogfight fixture.
3. **Read `pulp_noir/rules.yaml` in full** — same, for negotiation fixture.
4. **Read `encounter.rs` in full** — confirm `from_confrontation_def` signature and exact `StructuredEncounter` fields produced. Lock the hydration code to this shape.
5. **Read `dispatch_connect.rs` in full** — locate the exact insertion point for the CONFRONTATION emission. Confirm the `outgoing` vec (or equivalent) is in scope where the snapshot load completes.
6. **Read `ConnectScreen.tsx` and the session bootstrap flow in App.tsx** — locate `onAutoConnect` or the equivalent restore entry point. Confirm it's reusable; if not, factor it out as step 1 of the UI work.

Each of these is a 5-minute read. Do them in parallel at the start of execution.

---

## Sequencing

1. **Facts-on-the-ground pass** (30 min). Resolve all six open dependencies above. Log findings inline in the plan. If any finding invalidates the plan, stop and redesign before writing code.
2. **Create `sidequest-fixture` crate skeleton** (20 min). Cargo.toml, lib.rs, empty modules. Verify `cargo build --workspace` passes.
3. **Implement `schema.rs`** (30 min). Serde types + one round-trip unit test.
4. **Implement `hydrate.rs`** (60 min). Against poker fixture. Unit test asserts hydration produces a snapshot with non-None encounter and non-empty beats.
5. **Author `poker.yaml`** (20 min). Against verified spaghetti_western rules.
6. **Implement CLI binary** (30 min). `load`, `list`, `dump` subcommands. Manual test: `sidequest-fixture load poker` writes save file to disk.
7. **Fix dispatch_connect CONFRONTATION emission** (45 min). Including wiring test. Do this before the dev route — otherwise the dev route has nothing to verify against.
8. **Implement dev route module** (45 min). With `DEV_SCENES=1` gate. Manual test: `curl -X POST http://localhost:8080/dev/scene/poker` returns valid metadata and writes save.
9. **Implement UI query-param handler** (45 min). Test in browser: `http://localhost:5173?scene=poker` bypasses ConnectScreen and arrives at a live encounter.
10. **Write the integration test** (60-90 min). Iterate until green.
11. **Author `dogfight.yaml` and `negotiation.yaml`** (30 min). Each follows the poker pattern.
12. **Add justfile recipes** (15 min). End-to-end validation: `just scene poker`, `just scene dogfight`, `just scene negotiation`. All three land on the EncounterSheet.
13. **Code review checklist** (10 min). Run through item 6 of success criteria.

**Total estimate:** ~7 hours focused. Steps 2 and 7 can run in parallel (different crates, no shared files). Steps 9 and 11 can run in parallel.

---

## Done means

- All 7 success criteria green.
- The integration test in item 2 passes locally.
- Keith runs `just scene poker`, `just scene dogfight`, `just scene negotiation` and all three land on an active EncounterSheet within 10 seconds of the command.
- `dispatch_connect` CONFRONTATION-on-restore fix is in and tested (this is a bonus bug fix shipped inside the story).
- The two-phase dice plan (next) can use `load_fixture` + `POST /dev/scene/{name}` + `?scene=` as its test harness entry point with zero additions needed to the scene harness itself.
