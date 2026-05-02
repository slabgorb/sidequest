---
id: 69
title: "Scenario Fixtures — Pre-configured World States for Testing"
status: accepted
date: 2026-04-06
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [code-generation]
implementation-status: partial
implementation-pointer: 87
---

# ADR-069: Scenario Fixtures — Pre-configured World States for Testing

**Context:** Epic 24 (Procedural World-Grounding), prompt preview tooling

## Problem

Playtesting specific features (combat at low HP, dialogue with multiple NPCs,
chase sequences, trope beats at specific progression) requires 20-30 minutes of
play to reach the desired game state. This makes iterating on prompt quality,
verifying OTEL telemetry, and validating new subsystems impractically slow.

The existing scenario system (`scenarios/*.yaml`) drives player *actions* from a
fresh game start. There is no mechanism to start from a pre-configured mid-game
state.

## Decision

Introduce **scenario fixtures** — human-authored YAML files that describe a
partial `GameSnapshot` in a readable subset format. A CLI tool hydrates fixtures
into full `GameSnapshot` objects and writes them to the save directory via the
existing `SqliteStore` persistence layer. The existing `dispatch_connect()`
restore path picks them up with zero server changes.

## Design

### Fixture YAML Schema

Fixtures live in `scenarios/fixtures/` and describe the minimum state needed for
a test scenario. Unspecified fields use `GameSnapshot::default()`.

```yaml
# scenarios/fixtures/combat_low_hp.yaml
name: Combat at Low HP
genre: mutant_wasteland
world: flickering_reach

character:
  name: Rix
  class: Scavenger
  pronouns: they/them
  level: 3
  hp: 4
  max_hp: 22
  xp: 450
  inventory:
    - name: Rusty Pipe Wrench
      equipped: true
    - name: Flickering Lantern
    - name: Rad-Away
      quantity: 1
  gold: 12
  abilities: [Jury-Rig, Scav Sense, Rad Resistance]

location: The Collapsed Overpass
turn: 14

npcs:
  - name: Patchwork
    role: merchant
    disposition: friendly
  - name: Skitter
    role: scout
    disposition: wary

combat:
  in_combat: true
  turn_order: [Rix, Salt Burrower, Salt Burrower]
  current_turn: Rix
  enemies:
    - name: Salt Burrower
      hp: 14
      tier: 2
    - name: Salt Burrower
      hp: 8
      tier: 2

quests:
  The Signal Source: "find the origin of the radio signal (from: Toggler)"

# Optional sections — omit what you don't need
# tropes:
#   - id: mysterious_signal
#     progression: 0.45
# resources:
#   luck: 3.0
```

### CLI Binary: `sidequest-fixture`

New workspace crate following the `sidequest-namegen` pattern (~200 LOC).

```
sidequest-fixture load <fixture-name> [--player <name>]
  → reads scenarios/fixtures/<fixture-name>.yaml
  → hydrates into GameSnapshot (defaults for unspecified fields)
  → writes to ~/.sidequest/saves/<genre>/<world>/<player>/save.db
  → prints confirmation with key state summary

sidequest-fixture list
  → lists available fixtures with name + description

sidequest-fixture dump <fixture-name>
  → prints the full hydrated GameSnapshot as JSON (for debugging)
```

The `--player` flag defaults to `"fixture"` so fixtures don't collide with real
save files. The fixture name is the YAML filename without extension.

### Integration Points

#### 1. Playtest Scenarios

Existing scenario YAML gains an optional `fixture:` key:

```yaml
name: Combat Low HP Test
genre: mutant_wasteland
world: flickering_reach
fixture: combat_low_hp       # load this fixture before connecting
character:
  strategy: restore          # new: skip chargen, use existing save
  name: fixture              # matches --player default
actions:
  - "swing my wrench at the burrower"
  - "/status"
```

`playtest.py::run_scripted()` checks for `fixture:` and runs
`sidequest-fixture load <name>` before connecting the WebSocket.
`strategy: restore` tells the driver to skip character creation prompts.

#### 2. Prompt Preview

`sidequest-promptpreview` gains `--fixture <name>`:

```
sidequest-promptpreview --fixture combat_low_hp
```

Reads the fixture YAML and uses it to populate the Valley-zone game state
section instead of the static placeholder. Prompt evaluation now uses the
same state definitions as playtest scenarios.

### What This Does NOT Change

- **No new persistence code.** Uses existing `SqliteStore::save()`.
- **No new server code.** Uses existing `dispatch_connect()` restore path.
- **No new protocol messages.** The server sees a returning player with a save file.
- **No schema migration.** Fixtures produce standard `GameSnapshot` JSON.

## Hydration Rules

The fixture YAML is a **partial specification**. Hydration rules:

1. `genre_slug` and `world_slug` are required (top-level `genre:` and `world:`).
2. `character:` block hydrates into `characters[0]` on the snapshot.
3. `combat:` block hydrates into `CombatState` fields.
4. `npcs:` block creates `Npc` entries with `NpcCore` + optional `OceanProfile`.
5. `quests:` is a simple `HashMap<String, String>` — key is quest name, value is status.
6. `tropes:` creates `TropeState` entries with specified `id` and `progression`.
7. `resources:` populates `resource_state` HashMap.
8. All unspecified `GameSnapshot` fields use `Default::default()`.
9. `turn_manager.interaction` is set from `turn:` (defaults to 0).

## Starter Fixtures

Ship with the feature:

| Fixture | Tests |
|---------|-------|
| `combat_low_hp` | Combat at low HP, enemy already damaged |
| `three_npcs_dialogue` | Dialogue with multiple NPCs, active quests |
| `chase_in_progress` | Active chase sequence mid-pursuit |
| `mid_game_exploration` | Turn 14, established world, tropes at 40-60% |
| `fresh_start` | Turn 0, just-created character (baseline) |

## Consequences

### Positive

- Feature-specific testing drops from 30 minutes to seconds.
- Prompt engineers can evaluate prompts against specific game states.
- OTEL telemetry verification targets exact subsystem conditions.
- Fixtures are human-readable, version-controlled, and reviewable.
- New features can ship with a fixture that exercises them.
- Zero changes to production server code.

### Negative

- Fixture YAML schema must stay in sync with `GameSnapshot` evolution.
  Mitigation: the hydration code uses serde with `#[serde(default)]`, so
  new GameSnapshot fields are automatically defaulted. Only breaking
  renames require fixture updates.
- Fixtures bypass character creation. Tests that depend on chargen flow
  still need the existing `strategy: auto` path.

### Neutral

- Fixtures are a testing tool, not a save editor. Players never see them.

## Alternatives Considered

### A. Programmatic state builders (Rust test harness)

Rejected — useful for unit tests but doesn't help prompt engineers or
playtest drivers. YAML fixtures serve both.

### B. Save file snapshots (copy real .db files)

Rejected — opaque binary blobs, not reviewable, break on schema changes,
can't be parameterized.

### C. Extend playtest driver with setup actions

Rejected — still requires playing through 20+ turns. Slow and
non-deterministic.

## Implementation

| Item | Effort | Repo |
|------|--------|------|
| Fixture YAML serde types + hydration | ~150 LOC | api (sidequest-game) |
| `sidequest-fixture` CLI binary | ~200 LOC | api (new crate) |
| `--fixture` flag on `sidequest-promptpreview` | ~50 LOC | api |
| `fixture:` + `strategy: restore` in playtest driver | ~30 LOC | orchestrator |
| 5 starter fixtures | Content | orchestrator |
| Justfile recipes (`just fixture-load`, `just fixture-list`) | Trivial | orchestrator |

## Implementation status (2026-05-02)

The Rust era implemented this ADR — the `sidequest-fixture` crate exists at `sidequest-api/crates/sidequest-fixture/` with `hydrate.rs`, `schema.rs`, `error.rs`, and a `scene_harness_wiring` test. The 2026-04 port to Python did not carry the crate forward, but a **partial restoration was attempted with a meaningfully different design**, then left half-wired.

What is live:

- 4 fixture YAMLs in `scenarios/fixtures/` (`combat_test.yaml`, `dogfight.yaml`, `negotiation.yaml`, `poker.yaml`), schema-conformant to this ADR, all dated 2026-04-21.
- UI scene-harness in `sidequest-ui/src/App.tsx:1183–1213`: when the URL contains `?scene=NAME`, the client `POST /dev/scene/:name`, expects a `{slug}` response, and navigates to `/solo/:slug`. Fixture YAML headers document the expected URL form: `http://localhost:5173/?scene=combat_test (requires DEV_SCENES=1)`.

What is dark:

- The server `/dev/scene/{name}` endpoint — does not exist in `sidequest-server`. The UI POSTs into the void.
- A fixture hydrator function reading fixture YAML into a `GameSnapshot` — absent.
- The `sidequest-fixture` CLI binary — never created. `sidequest/cli/` contains namegen / encountergen / loadoutgen / validate / corpus* but no fixture module.
- `playtest.py` `fixture:` key handling — absent. The `strategy: restore` flag the ADR specifies is not parsed.
- `sidequest-promptpreview --fixture` — and indeed `promptpreview` itself — does not exist as a CLI module.

**Design pivot (unresolved).** The ADR specifies a CLI-driven flow: `sidequest-fixture load X` writes `save.db`, then `dispatch_connect()` restores it. What was actually wired (UI side only) is an HTTP-endpoint flow: `POST /dev/scene/X` stages a save, returns a slug, UI navigates to `/solo/:slug`. These are meaningfully different shapes. Restoration needs to pick one before continuing — the half-built UI side suggests the project drifted toward the HTTP design, but no ADR records that choice. A future amendment or successor ADR should resolve this.

Restoration is **P0 RESTORE** in [ADR-087](087-post-port-subsystem-restoration-plan.md): _"Zero occurrences in Python. Contradicts ADR-082's own justification (iteration speed is the product)."_ The "zero occurrences" framing is now stale — UI wiring and fixture YAMLs landed after that audit, leaving only the server-side hydrator + endpoint missing. ADR-087's row for this ADR is owed an update on its next pass.
