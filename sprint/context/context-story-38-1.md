---
parent: context-epic-38.md
workflow: tdd
---

# Story 38-1: ResolutionMode Enum + Field on ConfrontationDef

## Business Context

Every existing confrontation in SideQuest uses narrator-selected beats — one resolution
path. The dogfight subsystem needs a fundamentally different resolution: simultaneous
secret commits resolved via lookup table. This story adds the type-level distinction
that makes that possible without touching existing confrontation behavior.

This is pure type plumbing. Zero runtime impact. Every existing confrontation defaults
to `BeatSelection`. The value is that every downstream story (38-4, 38-5) can branch
on this enum instead of inventing ad-hoc detection logic.

## Technical Guardrails

### CLAUDE.md Wiring Rules (MANDATORY — applies to ALL stories in this epic)

1. **Verify Wiring, Not Just Existence.** Tests passing and files existing means nothing
   if the component isn't imported, the hook isn't called, or the endpoint isn't hit in
   production code. Check that new code has non-test consumers.

2. **Every Test Suite Needs a Wiring Test.** Unit tests prove a component works in
   isolation. That's not enough. Every set of tests must include at least one integration
   test that verifies the component is wired into the system — imported, called, and
   reachable from production code paths.

3. **No Silent Fallbacks.** If something isn't where it should be, fail loudly. Never
   silently try an alternative path, config, or default.

4. **No Stubbing.** Don't create stub implementations, placeholder modules, or skeleton
   code. If a feature isn't being implemented now, don't leave empty shells for it.

5. **Don't Reinvent — Wire Up What Exists.** Before building anything new, check if the
   infrastructure already exists in the codebase.

### Key Files

| File | Action |
|------|--------|
| `sidequest-api/crates/sidequest-genre/src/models/rules.rs` | Add `ResolutionMode` enum, add `resolution_mode` field to `ConfrontationDef` |
| `sidequest-api/crates/sidequest-genre/src/models/mod.rs` | Ensure `ResolutionMode` is re-exported |
| `sidequest-content/genre_packs/*/rules.yaml` | Verify existing packs deserialize correctly with default (no `resolution_mode` key = `BeatSelection`) |

### Patterns

- `ResolutionMode` must derive `Serialize, Deserialize, Debug, Clone, PartialEq`
- Use `#[serde(default)]` on the field so existing YAML without `resolution_mode` gets `BeatSelection`
- Follow the same derive pattern as existing enums in `rules.rs` (e.g., `MetricDirection`)

### Dependencies

- None. This is the foundation story — no prerequisites.

## Scope Boundaries

**In scope:**
- `ResolutionMode` enum with two variants: `BeatSelection`, `SealedLetterLookup`
- `resolution_mode: ResolutionMode` field on `ConfrontationDef` with serde default
- Serde round-trip tests (YAML and JSON)
- Backward compatibility test: deserialize existing genre pack `rules.yaml` files with no `resolution_mode` key and verify they get `BeatSelection`
- One integration test proving `ConfrontationDef` with `ResolutionMode` is reachable from `sidequest-server` (wiring test)

**Out of scope:**
- `commit_options`, `interaction_table`, or any other new fields on `ConfrontationDef` (38-4)
- Any runtime behavior change — no match arm, no dispatch logic (38-5)
- `per_actor_state` on `EncounterActor` (38-2)
- Modifying any existing confrontation YAML

## AC Context

**AC1: Enum exists with correct variants**
- `ResolutionMode::BeatSelection` and `ResolutionMode::SealedLetterLookup` compile
- Derives: `Serialize, Deserialize, Debug, Clone, PartialEq`
- Test: construct both variants, assert `!=`

**AC2: Field on ConfrontationDef with serde default**
- `ConfrontationDef.resolution_mode` exists, type `ResolutionMode`
- When `resolution_mode` is absent from YAML, defaults to `BeatSelection`
- Test: deserialize `ConfrontationDef` YAML without `resolution_mode` → assert `BeatSelection`
- Test: deserialize with `resolution_mode: sealed_letter_lookup` → assert `SealedLetterLookup`

**AC3: Existing packs unaffected**
- All genre packs in `sidequest-content/genre_packs/*/rules.yaml` deserialize without error
- All existing confrontation defs get `resolution_mode: BeatSelection`
- Test: load every active genre pack's rules, assert all confrontations are `BeatSelection`

**AC4: Wiring test**
- Integration test in `sidequest-server/tests/` that constructs a `ConfrontationDef` with
  `SealedLetterLookup`, proving the type is reachable from the server crate
- This is NOT a stub dispatcher — it's a type-reachability assertion

## Assumptions

- `ConfrontationDef` currently has no `resolution_mode` field (verify before implementing)
- Serde rename convention: `BeatSelection` → `beat_selection`, `SealedLetterLookup` → `sealed_letter_lookup` (snake_case in YAML)
- No changes needed to `StructuredEncounter` runtime — this story is types only
