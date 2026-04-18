---
parent: context-epic-38.md
workflow: tdd
---

# Story 38-4: Interaction Table Loader + `_from:` File Pattern

## Business Context

The dogfight's interaction table is a 422-line YAML file. Inlining that into `rules.yaml`
would make genre pack authoring miserable. This story adds a general-purpose `_from:`
loader pattern to the genre pack parser — any confrontation field can source its data
from an adjacent YAML file.

This is a one-time capability that benefits every future confrontation with large tables
(not just dogfight). The GM agent authors maneuvers and interaction cells in their own
files; the loader merges them into `ConfrontationDef` at parse time.

## Technical Guardrails

### CLAUDE.md Wiring Rules (MANDATORY)

1. **Verify Wiring, Not Just Existence.** The `_from:` loader must actually be called
   during genre pack loading. Not just defined. Verify the existing genre pack load path
   calls it.
2. **Every Test Suite Needs a Wiring Test.** Integration test that loads the space_opera
   genre pack with the dogfight files and verifies the confrontation def has populated
   `commit_options` and `interaction_table`.
3. **No Silent Fallbacks.** If a `_from:` path doesn't exist, PANIC. Don't silently
   skip it. Don't fall back to an empty table.
4. **No Stubbing.** The loader must actually parse the interaction table format, not
   return a placeholder.
5. **Don't Reinvent — Wire Up What Exists.** The genre pack loader already exists.
   Extend it. Don't build a parallel loading system.

### Key Files

| File | Action |
|------|--------|
| `sidequest-api/crates/sidequest-genre/src/models/rules.rs` | Add optional fields: `commit_options`, `interaction_table`, `descriptor_schema`. Add `_from:` serde aliases or custom deserializer. |
| `sidequest-api/crates/sidequest-genre/src/loader.rs` (or equivalent) | Extend genre pack loading to resolve `_from:` references relative to the genre pack root |
| `sidequest-content/genre_packs/space_opera/rules.yaml` | Add `dogfight` confrontation entry referencing `_from:` files |
| `sidequest-content/genre_packs/space_opera/dogfight/*.yaml` | Test fixtures — already authored content files |

### Patterns

- `_from:` is a CONVENTION, not a serde magic field. The loader detects `commit_options_from: dogfight/maneuvers_mvp.yaml` and resolves it at load time, populating `commit_options` on the `ConfrontationDef`. The final struct has no `_from` fields.
- Path resolution is relative to the genre pack root directory
- Every `_from:` reference that fails to resolve is a hard error (no silent fallback)

### Dependencies

- None for implementation. Parallel with 38-1, 38-2, 38-3.
- Content files already exist in `sidequest-content/genre_packs/space_opera/dogfight/`
- 38-5 depends on this for the interaction table to be available at runtime

## Scope Boundaries

**In scope:**
- `commit_options: Option<Vec<CommitOption>>` field on `ConfrontationDef` (or equivalent)
- `interaction_table: Option<InteractionTable>` field on `ConfrontationDef`
- `InteractionTable` struct with `cells: HashMap<(String, String), InteractionCell>`
- `InteractionCell` struct: `name`, `shape`, `actor_a_delta`, `actor_b_delta`, `narration_hint`
- `PerActorDelta` struct: `set_fields`, `metric_delta`, `secondary_delta`
- `_from:` loader: resolve file references at genre pack load time
- Load test: parse `space_opera/dogfight/interactions_mvp.yaml` → 16 cells
- Load test: parse `space_opera/dogfight/maneuvers_mvp.yaml` → 4 maneuvers
- Wiring test: full genre pack load of space_opera produces a `dogfight` confrontation with populated interaction table

**Out of scope:**
- Runtime resolution logic (38-5 consumes the loaded table)
- Descriptor schema validation of cell deltas (open question — recommended at load time)
- Adding the `dogfight` entry to `rules.yaml` for other genre packs (space_opera only for MVP)
- The `ResolutionMode` field (38-1 — but 38-4 should work with it if 38-1 is merged first)

## AC Context

**AC1: New types compile and serialize**
- `InteractionTable`, `InteractionCell`, `PerActorDelta`, `CommitOption` structs exist
- Serde round-trip: construct → serialize → deserialize → assert equality
- Test with real data from `interactions_mvp.yaml` format

**AC2: `_from:` loader resolves file references**
- Genre pack loader sees `commit_options_from: dogfight/maneuvers_mvp.yaml` on a confrontation def
- Resolves path relative to genre pack root
- Parses the referenced file into the correct type
- Populates `commit_options` on the `ConfrontationDef`
- Test: mock genre pack with `_from:` reference, verify populated

**AC3: Missing `_from:` file is a hard error**
- If `commit_options_from:` points to a nonexistent file, the loader returns `Err`
- NOT a silent empty default. NOT a warning-and-continue.
- Test: reference nonexistent file, assert error

**AC4: Full integration — space_opera dogfight loads**
- Load the space_opera genre pack with the real `dogfight/` content files
- The resulting `ConfrontationDef` for type `dogfight` has:
  - 4 commit options (straight, bank, loop, kill_rotation)
  - 16 interaction cells (all 4x4 permutations)
  - Each cell has narration_hint, per-actor deltas
- This is the wiring test — proves the loader is called during real genre pack loading

**AC5: Existing packs unaffected**
- Genre packs without any `_from:` references load identically to before
- No new required fields, no behavioral change for packs that don't use the feature

## Assumptions

- The genre pack loader reads `rules.yaml` relative to the pack directory (verify loader implementation)
- `serde_json::Value` is available in `sidequest-genre` (verify Cargo.toml dependencies)
- The `_from:` pattern is a loader-level concern, not a serde-level concern — the deserialized struct has populated fields, not file paths
