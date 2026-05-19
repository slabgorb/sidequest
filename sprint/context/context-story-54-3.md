---
parent: context-epic-54.md
workflow: tdd
---

# Story 54-3: `pf validate locations` — well-formedness + binding resolution + prose-manifest coherence

## Business Context

A new CLI validator alongside the existing `pf validate {adr, agent, sprint, context, ...}` family. Three checks per genre pack, per world:

| Check | Failure |
|---|---|
| **Manifest well-formedness** — every `entities[*]` row parses as `LocationEntity`; no duplicate ids within a region/room; no `binding` when `tier != real_object`; no empty `label`. | Hard error. |
| **Binding resolution** — for entities with `binding.kind in {npc, item, clue, scenario_clue}`, the `ref` resolves in the target subsystem. `location_feature` is free-form (id unique within region). | Hard error. |
| **Prose-manifest coherence** — loader scans `description` for proper-noun-shaped tokens and definite-article phrases ("the X"); each must resolve to an entity, an NPC name, or a per-pack `generic_allowlist[]` entry. | Warning (non-blocking). |

Hard-error checks gate CI. Warning check is observable but never blocking. The server's runtime loader does NOT re-validate — it trusts content that passed the validator.

**Audience:** Content authors (Keith mostly) writing or backfilling cartography manifests; CI reviewers; future agents.

**Expected outcome:** `pf validate locations <pack> [<world>]` is a real, callable CLI. CI integration blocks merges on hard errors. Programmatic entry exists so Story 55-1's post-materialize smoke test can call it.

## Technical Guardrails

**Implementation plan:** `docs/superpowers/plans/2026-05-19-story-54-3-pf-validate-locations.md` — task-by-task TDD guide.

**Key files:**
- `sidequest-server/sidequest/cli/validate/` — the existing `pf validate` family. New `locations.py` module + CLI command registration.
- `sidequest-server/sidequest/protocol/models.py` — `LocationEntity` (from 54-2) is the validation target.
- `sidequest-content/genre_packs/<pack>/worlds/<world>/cartography.yaml` — POI input.
- `sidequest-content/genre_packs/<pack>/worlds/<world>/rooms/<id>.yaml` — procedural input.
- `sidequest-content/genre_packs/<pack>/npcs.yaml` — NPC ref-resolution target.
- `sidequest-content/genre_packs/<pack>/pack.yaml` (or wherever pack config lives) — for the `generic_allowlist[]` per-pack key.

**Patterns to follow:**
- Mirror the existing `pf validate adr` / `pf validate context` CLI shape (Click commands, JSON+text reporters, exit code 1 on hard error, exit code 0 on warning-only).
- Validator is **content-time**, not runtime — never imported by the server's hot path.
- Per-pack `generic_allowlist[]` is the escape hatch for "Tuesday", "Highland", etc. — warn only when un-allowlisted AND un-resolved.

**What NOT to touch:**
- Runtime loader (`room_file_loader.py`) — trust the validator output, never re-check at runtime.
- The pydantic models themselves (54-2 owns those).
- Authored content beyond what the test fixtures need.

## Scope Boundaries

**In scope:**
- New `pf validate locations` CLI command.
- Programmatic entry `validate_locations_in_world(world_dir)` (or equivalent) for 55-1's post-materialize smoke test.
- Hard-error checks (well-formedness, binding resolution) + warning check (prose-manifest coherence).
- Per-pack `generic_allowlist[]` plumbing.
- CI gate (job in the existing CI config) that runs the validator across every wired genre pack.
- Test fixtures: well-formed, malformed, and warning-triggering YAML samples.

**Out of scope:**
- Server runtime use of the validator (the contract is content-time only).
- Authoring `generic_allowlist[]` entries for every pack — only the test fixtures plus any pack the tests cover. Real authoring lands incidentally during 54-4 / 54-5.
- Procedural validator post-check call from materializer code — that's 55-1's job.

## AC Context

**AC-1:** `pf validate locations <pack>` runs every wired world in the pack; exit code 1 on any hard error, 0 otherwise.

**AC-2:** Well-formedness check rejects: duplicate `id` within a region, `binding` on `tier=flavor_only`, blank `label`, blank `id`, extra fields.

**AC-3:** Binding resolution check resolves `binding.kind in {npc, item, clue, scenario_clue}` against the target subsystem (npcs.yaml etc.). Unresolved refs are hard errors with file:line refs.

**AC-4:** Prose-manifest coherence scans `description` for proper-noun-shaped tokens and "the X" phrases; warns on tokens not in `entities[].label`, `npcs.yaml`, or per-pack `generic_allowlist[]`. Warnings carry file:line context. Warnings never fail the exit code.

**AC-5:** Programmatic entry (`validate_locations_in_world(world_dir) -> ValidationReport` or equivalent) returns a structured result with `.errors` and `.warnings` lists. Story 55-1's integration test calls this.

**AC-6:** CI runs `pf validate locations` on every wired pack as part of `just check-all` (or as a CI job entry). The pre-existing 5 wired packs all pass (warnings allowed; the prose-coherence warnings are documented in the report, never hard-error).

**AC-7:** A wiring test asserts the CLI subcommand is registered (importable + listed in `pf validate --help`) and that the programmatic entry has a non-test caller via 55-1 (or, until 55-1 lands, the test asserts the function exists with the documented signature so 55-1 can call it).
