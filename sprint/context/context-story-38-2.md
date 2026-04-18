---
parent: context-epic-38.md
workflow: tdd
---

# Story 38-2: per_actor_state on EncounterActor

## Business Context

Existing encounters track state at the encounter level — one shared metric, shared
secondary stats. Dogfights need per-pilot state: each pilot has their own bearing,
range, energy, gun_solution. This story adds the `per_actor_state` field that holds
each actor's scene descriptor independently.

This is the load-bearing data structure for the entire dogfight subsystem. Without it,
there's nowhere to store per-pilot descriptors between turns, and the narrator has
nothing to render cockpit POV from.

## Technical Guardrails

### CLAUDE.md Wiring Rules (MANDATORY)

1. **Verify Wiring, Not Just Existence.** Check that new code has non-test consumers.
2. **Every Test Suite Needs a Wiring Test.** Include at least one integration test
   verifying the component is wired into the system — imported, called, and reachable
   from production code paths.
3. **No Silent Fallbacks.** Fail loudly if state is missing or malformed.
4. **No Stubbing.** No empty `per_actor_state` wrappers that "will be filled later."
5. **Don't Reinvent — Wire Up What Exists.** `EncounterActor` already exists. Extend it.

### Key Files

| File | Action |
|------|--------|
| `sidequest-api/crates/sidequest-game/src/encounter.rs` | Add `per_actor_state: HashMap<String, serde_json::Value>` to `EncounterActor` |
| `sidequest-api/crates/sidequest-game/src/encounter.rs` | Ensure serde derives handle the new field (default to empty HashMap) |

### Patterns

- Use `#[serde(default)]` so existing saved encounters without `per_actor_state` deserialize as empty HashMap
- The field is `HashMap<String, serde_json::Value>` — typed-Value escape hatch. Schema validation happens at genre pack load time (38-4), not at runtime
- Follow existing patterns in `EncounterActor` for derive macros and serde attributes

### Dependencies

- None. Parallel with 38-1, 38-3, 38-4.

## Scope Boundaries

**In scope:**
- `per_actor_state: HashMap<String, serde_json::Value>` field on `EncounterActor`
- Serde round-trip tests (serialize with populated state, deserialize back, assert equality)
- Backward compat: deserialize saved encounter JSON without `per_actor_state` → empty HashMap
- Save/load preservation: create encounter with per_actor_state, serialize to the save format, deserialize, verify state survives
- Wiring test: integration test in `sidequest-server/tests/` proving `EncounterActor.per_actor_state` is accessible from server crate

**Out of scope:**
- Schema validation against `descriptor_schema.yaml` (deferred — load-time validation lands with 38-4)
- Any code that WRITES to `per_actor_state` (38-5 does that)
- Any code that READS from `per_actor_state` for narration (38-6 does that)
- `ResolutionMode` (38-1)

## AC Context

**AC1: Field exists with correct type**
- `EncounterActor.per_actor_state` is `HashMap<String, serde_json::Value>`
- Populated with example descriptor fields (bearing, range, energy, gun_solution)
- Test: construct actor with state, read fields back, assert values

**AC2: Serde round-trip**
- Serialize `EncounterActor` with populated `per_actor_state` to JSON
- Deserialize back
- Assert all fields survive including nested Value types (strings, numbers, booleans)
- Test: include at least one field of each Value variant used by descriptors (String, Number, Bool)

**AC3: Backward compatibility**
- Deserialize existing encounter JSON (without `per_actor_state` key) → succeeds
- `per_actor_state` is empty HashMap
- Test: hand-crafted JSON representing a pre-38-2 saved encounter, assert clean deser

**AC4: Save/load round-trip**
- Full save path: create StructuredEncounter with actors that have per_actor_state,
  save to SQLite (or whatever the current save format is), load back, verify state intact
- This tests the FULL persistence pipeline, not just serde

**AC5: Wiring test**
- Integration test in `sidequest-server/tests/` that constructs an `EncounterActor` with
  `per_actor_state` and accesses it through the server's encounter handling path
- Must be a non-test consumer or a test that proves reachability from production code

## Assumptions

- `EncounterActor` already derives `Serialize, Deserialize` (verify before implementing)
- `serde_json` is already a dependency of `sidequest-game` (verify Cargo.toml)
- Save format is SQLite with JSON-serialized game state (verify save/load path)
