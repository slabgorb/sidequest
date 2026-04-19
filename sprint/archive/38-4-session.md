---
story_id: "38-4"
jira_key: null
epic: "38"
workflow: "tdd"
---
# Story 38-4: Interaction table loader and _from file pattern

## Story Details
- **ID:** 38-4
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 3
- **Repos:** api, content

## Acceptance Criteria
- [ ] Interaction table loader can source confrontation sub-files from adjacent YAML (genre pack loader pattern)
- [ ] Unit tests on space_opera dogfight fixtures verify the loading behavior
- [ ] Pattern supports genre pack organization of complex encounter data

## Workflow Tracking
**Workflow:** tdd
**Phase:** verify
**Phase Started:** 2026-04-13T17:59:58Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-13T14:00Z | 2026-04-13T17:25:36Z | 3h 25m |
| red | 2026-04-13T17:25:36Z | 2026-04-13T17:33:09Z | 7m 33s |
| green | 2026-04-13T17:33:09Z | 2026-04-13T17:59:18Z | 26m 9s |
| spec-check | 2026-04-13T17:59:18Z | 2026-04-13T17:59:58Z | 40s |
| verify | 2026-04-13T17:59:58Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): No epic-38 context file exists in `sprint/context/` and no story-38-4 context either. Affects `sprint/context/` (would help future agents on epic 38 stories). *Found by TEA during test design.*
- **Improvement** (non-blocking): `InteractionTable` is a new cross-cutting type; `sidequest-game`'s confrontation engine will eventually need to consume it for sealed-letter lookup turns. Affects `sidequest-api/crates/sidequest-game/` (future wiring — not in this story's scope, but worth a follow-up story so the Dev doesn't ship a type with no runtime consumer). *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): `spaghetti_western/rules.yaml` had three `custom_rules` entries typed as YAML booleans (`standoff: true`, `bounty_board: true`, `luck_as_resource: true`) under a `HashMap<String, String>` field. The pre-existing `load_yaml::<RulesConfig>` path silently coerced booleans to strings, but the new `load_rules_config` path (which goes via `serde_yaml::Value` as an intermediate) is stricter and refuses the coercion. Affects `sidequest-content/genre_packs/spaghetti_western/rules.yaml` (booleans converted to string literals — fix committed as 9b28b58 on the 38-4 content branch). This was a pre-existing latent bug exposed by the stricter pipeline; worth a follow-up audit to check other genre packs for similar string-typed fields holding non-string scalars. *Found by Dev during implementation.*
- **Improvement** (non-blocking): The 38-1 regression test `all_genre_packs_load_after_resolution_mode_addition` had a blanket "every confrontation defaults to BeatSelection" assertion. 38-4 legitimately introduces space_opera's dogfight as `sealed_letter_lookup`, so the test was updated to pin expected value per-confrontation (commit 25cf5df on the 38-4 api branch). If future stories add more sealed-letter confrontations, that list will grow — a cleaner long-term shape would iterate pack.rules.confrontations and assert each matches the declared mode in rules.yaml rather than hardcoding exceptions. Affects `sidequest-api/crates/sidequest-genre/tests/resolution_mode_story_38_1_tests.rs`. *Found by Dev during implementation.*

## TEA Assessment

**Phase:** verify
**Tests Required:** Yes
**Status:** RED (fails to compile — 4 missing symbols)

**Test File:**
- `sidequest-api/crates/sidequest-genre/tests/interaction_table_loader_story_38_4_tests.rs` — 12 tests, 585 lines

**Tests Written:** 12 tests covering 3 ACs plus project principles

### AC Coverage

| AC | Tests |
|----|-------|
| AC-1: Loader sources confrontation sub-files via `_from` | `load_rules_config_resolves_from_pointer_on_interaction_table`, `load_rules_config_preserves_inline_confrontations_regression` |
| AC-2: Unit tests on space_opera dogfight fixtures | `standalone_interaction_table_loader_parses_real_space_opera_fixture`, `space_opera_loads_end_to_end_with_from_pointer_wired_in` |
| AC-3: Pattern supports complex encounter data organisation | All `_from` tests — `_from` is field-scoped and generic over any sub-structure |

### Project Principle Coverage

| Principle | Test |
|-----------|------|
| No silent fallbacks | `load_rules_config_fails_loudly_when_from_target_is_missing`, `load_interaction_table_fails_loudly_on_missing_file` |
| No path traversal | `load_rules_config_rejects_absolute_from_path`, `load_rules_config_rejects_parent_directory_traversal` |
| Every test suite needs a wiring test | `space_opera_loads_end_to_end_with_from_pointer_wired_in` — forces Dev to wire `load_rules_config` into `load_genre_pack` AND update `space_opera/rules.yaml` to actually use a `_from` pointer (content repo change is in scope — repos: api,content) |

### Rule Coverage (lang-review/rust.md)

| Rule | Test | Status |
|------|------|--------|
| #5 validated constructors | `interaction_table_rejects_empty_version`, `interaction_table_rejects_empty_cells` | compile-fail (RED) |
| #8 Deserialize bypass | `interaction_table_rejects_empty_cells` / `_rejects_duplicate_cell_pairs` — force `#[serde(try_from)]` on `InteractionTable` | compile-fail (RED) |
| #13 Constructor/Deserialize consistency | Same try_from pattern — all deserialization paths run validation | compile-fail (RED) |
| #15 Unbounded recursive input | `load_rules_config_rejects_nested_from_pointers` | compile-fail (RED) |
| #6 Test quality (self-check) | All tests have meaningful `assert_eq!` or structural match assertions; no `let _ = result;`, no `assert!(true)`, no vacuous `is_none()` on always-None values | passes self-check |

**Rules N/A for this change:** #1 silent errors, #2 non_exhaustive (no new public enums), #3 placeholders, #4 tracing, #7 `as` casts, #9 public fields (existing convention — all genre model fields are public), #10 tenant context (no trait work), #11 workspace deps, #12 dev-deps (tempfile already in dev-dependencies), #14 fix regressions (not a fix PR).

### RED State Verification

testing-runner confirmed compile-failure with exactly the 4 expected missing symbols:
- `sidequest_genre::InteractionTable` (E0432 — type doesn't exist)
- `sidequest_genre::load_interaction_table` (E0432 — fn not exported)
- `sidequest_genre::load_rules_config` (E0432 — fn not exported)
- `ConfrontationDef.interaction_table` (E0609 — field doesn't exist)

No unrelated Rust errors. This is the correct TDD RED state.

### Implementation Guidance for Dev

Dev will need to:

1. **New model:** `InteractionTable` with `version: String`, `starting_state: String`, `maneuvers_consumed: Vec<String>`, `cells: Vec<InteractionCell>`. Use `#[serde(try_from = "RawInteractionTable")]` and validate in `TryFrom`: reject empty version, empty cells, duplicate `(red, blue)` pair keys. `InteractionCell` holds `pair: (String, String)`, `name`, `shape`, `red_view: serde_yaml::Value`, `blue_view: serde_yaml::Value`, `narration_hint: String`. (Keep the view payloads as untyped `Value` for now — a future story can narrow them to a typed descriptor once the engine consumes the data.) The YAML uses `pair: [red, blue]` — map to the tuple via a raw `Vec<String>` in the Raw type and validate length == 2 in `TryFrom`.

2. **New loader fn:** `pub fn load_interaction_table(path: &Path) -> Result<InteractionTable, GenreError>` — thin wrapper over `load_yaml` with a `GenreError::LoadError` on missing file (no silent `None` fallback).

3. **New loader fn:** `pub fn load_rules_config(rules_path: &Path, pack_dir: &Path) -> Result<RulesConfig, GenreError>`. Algorithm:
   - Read `rules.yaml` as `serde_yaml::Value`.
   - Walk `confrontations[].interaction_table` entries. If the value is a mapping containing a single `_from` key, resolve:
     - Reject absolute paths. Reject any component containing `..`. (Use `Path::components()` to walk safely — do NOT rely on canonicalize, which can symlink-escape.)
     - Compute `pack_dir.join(rel_path)`.
     - Read the file as `serde_yaml::Value`.
     - If the loaded value itself contains `_from` at the top level, reject (no nested chains).
     - Substitute the loaded value in place of the `{_from: ...}` mapping.
   - Deserialize the resolved tree into `RulesConfig` via `serde_yaml::from_value`. All existing validation (`ConfrontationDef::try_from`, `InteractionTable::try_from`) runs automatically on the resolved tree.

4. **Add field:** `ConfrontationDef.interaction_table: Option<InteractionTable>` (with matching `#[serde(default)]`), and the same on `RawConfrontationDef`.

5. **Wire into `load_genre_pack`:** replace `let rules: RulesConfig = load_yaml(&path.join("rules.yaml"))?;` with `let rules: RulesConfig = load_rules_config(&path.join("rules.yaml"), path)?;`.

6. **Content change:** `sidequest-content/genre_packs/space_opera/rules.yaml` — add a dogfight confrontation entry with `resolution_mode: sealed_letter_lookup` and `interaction_table: { _from: dogfight/interactions_mvp.yaml }`. This is what makes the `space_opera_loads_end_to_end_with_from_pointer_wired_in` test go green.

**Exports to add to `lib.rs`:** `InteractionTable`, `InteractionCell`, `load_interaction_table`, `load_rules_config` (or re-exported via `pub use models::*;` for the types and `pub use loader::*` expansion for the functions).

**Handoff:** To Dev (Charles) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 336/336 passing (full `sidequest-genre` suite GREEN, including all 12 new story-38-4 tests)
**Branches:** All pushed to `origin`
- `sidequest-api` → `feat/38-4-interaction-table-loader-from-pattern` (commits: 1289e2d test, 25cf5df test-update, 9b7dc2a impl)
- `sidequest-content` → `feat/38-4-interaction-table-loader-from-pattern` (commits: 9b28b58 spaghetti_western fix, 0f09558 space_opera dogfight `_from` wire-up)
- orchestrator → `feat/38-4-interaction-table-loader-from-pattern` (session file pending final commit by SM)

### Files Changed

**sidequest-api (Rust implementation):**
- `crates/sidequest-genre/src/models/rules.rs` — `+190` lines
  - New `RawInteractionCell` / `InteractionCell` with validated `TryFrom` (pair length == 2)
  - New `RawInteractionTable` / `InteractionTable` with validated `TryFrom` (non-empty version, non-empty cells, unique `(red, blue)` pairs)
  - `RawConfrontationDef.interaction_table: Option<InteractionTable>` (with `#[serde(default)]`)
  - `ConfrontationDef.interaction_table: Option<InteractionTable>` (with `#[serde(default, skip_serializing_if = "Option::is_none")]`)
  - `TryFrom<RawConfrontationDef>` passes the field through
- `crates/sidequest-genre/src/loader.rs` — `+135` lines
  - `pub fn load_interaction_table(path) -> Result<InteractionTable, GenreError>` — thin wrapper over `load_yaml`
  - `pub fn load_rules_config(rules_path, pack_dir) -> Result<RulesConfig, GenreError>` — reads `rules.yaml` as `serde_yaml::Value`, walks `confrontations[].interaction_table`, substitutes `{ _from: rel }` mappings with resolved sub-file content, then deserializes the merged tree into `RulesConfig` (running all existing `TryFrom` validators)
  - Private helpers: `resolve_confrontation_from_pointers`, `extract_from_pointer`, `resolve_from_pointer`
  - Path safety via `Path::components()` — rejects `Component::ParentDir`, `Component::RootDir`, `Component::Prefix` before touching the filesystem
  - Nested `_from` chains rejected post-read (Rule #15 — no unbounded recursive input)
  - `load_genre_pack` now calls `load_rules_config(&path.join("rules.yaml"), path)` instead of the direct `load_yaml::<RulesConfig>` — wires the feature into every production consumer
- `crates/sidequest-genre/src/lib.rs` — `+1` line
  - Re-exports `load_interaction_table` and `load_rules_config` alongside `load_genre_pack`
- `crates/sidequest-genre/tests/resolution_mode_story_38_1_tests.rs` — `+10 -3`
  - Regression test updated to expect `SealedLetterLookup` for space_opera's new dogfight confrontation (see deviation entry #1)

**sidequest-content (genre pack data):**
- `genre_packs/space_opera/rules.yaml` — `+24` lines
  - New `dogfight` confrontation with `resolution_mode: sealed_letter_lookup` and `interaction_table: { _from: dogfight/interactions_mvp.yaml }`
  - References the existing 16-cell 4x4 maneuver grid fixture — no content duplication
- `genre_packs/spaghetti_western/rules.yaml` — `+3 -3`
  - `custom_rules` booleans converted to string literals (see deviation entry #2)

### AC Coverage → Tests

| AC | Tests | Result |
|----|-------|--------|
| AC-1: Loader sources confrontation sub-files via `_from` | `load_rules_config_resolves_from_pointer_on_interaction_table`, `load_rules_config_preserves_inline_confrontations_regression` | PASS |
| AC-2: Unit tests on space_opera dogfight fixtures | `standalone_interaction_table_loader_parses_real_space_opera_fixture`, `space_opera_loads_end_to_end_with_from_pointer_wired_in` | PASS |
| AC-3: Pattern supports complex encounter data organisation | All `_from` tests — field-scoped resolver generic over any sub-structure | PASS |

### Wiring Verification

The wiring test `space_opera_loads_end_to_end_with_from_pointer_wired_in` loads the real `space_opera` genre pack via the production `load_genre_pack` entry point, finds the `SealedLetterLookup` confrontation, asserts its `interaction_table` is populated with 16 cells. This is only possible when:
1. `load_rules_config` is wired into `load_genre_pack` ✅
2. The `_from` resolver correctly reads and substitutes sub-file content ✅
3. `space_opera/rules.yaml` actually uses the `_from` pointer to reference the dogfight fixture ✅
4. `ConfrontationDef` has the `interaction_table` field and it deserializes ✅
5. The real `dogfight/interactions_mvp.yaml` fixture passes all validators (non-empty, unique pairs) ✅

All five halves present — no half-wired feature.

### Self-Review Checklist

- [x] Code is wired to production consumers — `load_rules_config` replaces the direct `load_yaml` call in `load_genre_pack`, so every pack loaded anywhere in the workspace flows through the new resolver.
- [x] Code follows project patterns — validated domain types use the same `#[serde(try_from)]` pattern as `ConfrontationDef`, `MetricDef`, `BeatDef`; loader helpers use the same `load_error` / `GenreError::LoadError` shape.
- [x] All acceptance criteria met — see AC coverage table above.
- [x] Error handling — all filesystem / parse paths return `GenreError::LoadError` with the offending path in the message; path-safety errors are rejected before any filesystem read.
- [x] No silent fallbacks — missing `_from` targets, absolute paths, `..` components, nested chains, and type-mismatched content all surface as `LoadError`.
- [x] Rust rules check — no `.ok()` / `.expect()` on user-controlled paths; no `as` casts; no public fields with security invariants; no new enums (`#[non_exhaustive]` N/A).

**Handoff:** To Colonel Sherman Potter (Reviewer) for review phase.

## Sm Assessment

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec. The story ACs map 1:1 to tests — the only design choice that was not spelled out in the spec is that `_from` pointers are scoped to the `interaction_table` field rather than replacing a whole confrontation body. That reading matches the story title ("Interaction table loader AND _from file pattern") and the existing on-disk layout of `space_opera/dogfight/` (table is the nested complex structure that needs extraction; the rest of the confrontation is small and stays inline). Logged here as a design decision rather than a deviation.

### Dev (implementation)
- **Edited a test file from another story (38-1)**
  - Spec source: TEA assessment (session file), implementation guidance step 5-6
  - Spec text: "Wire `load_rules_config` into `load_genre_pack` … Content change: `space_opera/rules.yaml` — add a dogfight confrontation entry with `resolution_mode: sealed_letter_lookup`"
  - Implementation: Also modified `resolution_mode_story_38_1_tests.rs::all_genre_packs_load_after_resolution_mode_addition` to expect `SealedLetterLookup` for the new space_opera dogfight confrontation
  - Rationale: The 38-1 regression test asserted every confrontation in every pack defaults to `BeatSelection`. Adding a legitimate `sealed_letter_lookup` confrontation to space_opera breaks that blanket invariant. Updating the 38-1 test to pin expected value per-confrontation is the correct follow-through — not a weakening of the assertion, just an update of what it measures. Alternative (skipping space_opera or dogfight) would have silently hidden the new state from the regression guard.
  - Severity: minor
  - Forward impact: minor — future stories adding more `sealed_letter_lookup` confrontations will need to extend the per-confrontation match block, or refactor the test to iterate via the declared-mode source of truth in rules.yaml.
- **Fixed a pre-existing latent bug in spaghetti_western genre pack**
  - Spec source: CLAUDE.md "No Silent Fallbacks" principle
  - Spec text: "If something isn't where it should be, fail loudly. Never silently try an alternative path, config, or default."
  - Implementation: Changed `standoff: true`, `bounty_board: true`, `luck_as_resource: true` to quoted string literals in `spaghetti_western/rules.yaml`
  - Rationale: The old `serde_yaml::from_str::<RulesConfig>()` pipeline silently coerced YAML booleans into String fields. The new `load_rules_config` goes via `serde_yaml::Value` as an intermediate step, which surfaces the type mismatch. Rather than revert to lax coercion (which is itself a silent fallback), fix the genre pack so the YAML matches the declared schema. This is in scope per the "fixes and broken-test hygiene are never scope creep" memory — the alternative is shipping a loader that silently paves over content bugs.
  - Severity: minor
  - Forward impact: none — the fix is purely in content data and carries no API surface.

## Sm Assessment

**Scope:** Extend genre pack loader so a confrontation (and its interaction tables / maneuvers / pilot skills) can be split across an adjacent sub-directory via a `_from:` pointer, rather than inlined in `rules.yaml`. Reference fixture: `sidequest-content/genre_packs/space_opera/dogfight/` already contains `interactions_mvp.yaml`, `maneuvers_mvp.yaml`, `pilot_skills.yaml`, `descriptor_schema.yaml` — the intended shape is already on disk, we are wiring the loader to honor it.

**Key files (read-only signals for TEA):**
- `sidequest-api/crates/sidequest-genre/src/models/rules.rs` — `RawConfrontationDef` / `try_from` (line 309+); extension point for `_from` resolution
- `sidequest-api/crates/sidequest-genre/src/` — existing loader entrypoints (likely `lib.rs` / `loader.rs`) for pack-relative path resolution
- `sidequest-content/genre_packs/space_opera/dogfight/` — fixtures for unit tests
- `sidequest-content/genre_packs/space_opera/rules.yaml` — where the `_from:` reference will live

**TDD targets (for TEA to author as RED tests):**
1. Loader resolves a confrontation whose body is `_from: dogfight/` (or equivalent) — merged result has interactions, maneuvers, pilot skills populated from the sub-files.
2. Missing `_from` target fails loudly (no silent fallback — matches project principle).
3. Path traversal / absolute paths rejected; `_from` is always pack-relative.
4. Existing inline confrontations still load (regression guard).

**Risks / watch-outs:**
- `_from` must compose with the current `RawConfrontationDef::try_from` pipeline without breaking serde tagging. TEA should sketch the on-disk YAML shape in the test fixtures so Dev has a concrete target.
- No silent fallbacks: if a sub-file is absent, surface the path in the error.
- Wiring check: the loader change must be consumed by the existing genre pack load path in `sidequest-server` startup — not a dangling helper. Integration test should assert a full `GenrePack` load of `space_opera` still succeeds end-to-end.

**Workflow:** TDD phased — next owner is TEA (RED).