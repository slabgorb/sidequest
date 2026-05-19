---
parent: context-epic-54.md
workflow: trivial
---

# Story 54-4: Content backfill — `tea_and_murder/glenross` regions to typed `entities[]`

## Business Context

Convert the 12 hand-authored `regions[*].landmarks: list[str]` entries in `tea_and_murder/glenross/cartography.yaml` into the typed `entities[]` shape that 54-2 introduced. Add `binding` entries for entities that already correspond to authored NPCs (Mrs Bairnsley, the verger, etc.) or scenario clues (the misdelivered letter, the bell, the locked vestry door, etc.).

**Audience:** Sonia (the `tea_and_murder` pack is the love letter described in `CLAUDE.md`'s "Who This Is For"). She is **aspirational audience**, not load-bearing — but the pack is the cleanest demonstration surface for the manifest because its prose is the densest and its NPCs are the most named. Validator-clean glenross is the demo content for "see how this would look for Sonia."

**Expected outcome:** The 12 region descriptions still read identically to a player. The new `entities[]` arrays carry one `LocationEntity` per noun the prose names that resolves to a real game-state thing, plus `flavor_only` rows for set-dressing the validator's prose-coherence check would otherwise warn on. `pf validate locations tea_and_murder glenross` is clean (zero hard errors, ideally zero warnings).

## Technical Guardrails

**Implementation plan:** `docs/superpowers/plans/2026-05-19-story-54-4-glenross-entities-backfill.md` — task-by-task content-authoring guide listing each region and the entity rows to add.

**Key files:**
- `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/cartography.yaml` — the 12-region source.
- `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/npcs.yaml` — NPC ids that bindings reference.
- `sidequest-content/genre_packs/tea_and_murder/worlds/glenross/scenarios/` — scenario clue ids for `clue` / `scenario_clue` bindings.
- `sidequest-content/genre_packs/tea_and_murder/pack.yaml` (or equivalent) — `generic_allowlist[]` additions for words like "Tuesday", "the weather", "the village" that surface in glenross prose but should NOT be flagged.

**Patterns to follow:**
- Authored YAML — pure content edit.
- Three-tier model (54-2 / ADR-109): `real_object` for anything mechanical (NPC presence, scenario clue, location feature with affordances); `flavor_only` for set-dressing only the prose mentions; `yes_and` is reserved for runtime promotions — content authoring NEVER uses `yes_and`.
- Keep the legacy `landmarks[]` array intact if the loader still consumes it for pre-54 code paths (54-2 keeps it as backcompat). Real removal is a separate later story once every pack is backfilled.

**What NOT to touch:**
- The 5 other genre packs (`caverns_and_claudes`, `elemental_harmony`, `mutant_wasteland`, `space_opera`, `tea_and_murder`'s other worlds) — out of scope; each gets its own backfill story when there's a reason.
- The validator itself (54-3).
- Any code.

## Scope Boundaries

**In scope:**
- Typed `entities[]` block on all 12 glenross regions.
- Bindings to existing NPCs / scenario clues / location features.
- Per-pack `generic_allowlist[]` additions for unflagged prose words.
- Validator pass: `pf validate locations tea_and_murder glenross` exits 0 with zero hard errors.

**Out of scope:**
- Any other pack.
- New NPCs or scenario clues introduced just to satisfy bindings — the existing referents are the universe.
- Rewriting the prose itself. Prose stays as-authored; the manifest is *added*, not *re-derived*.

## AC Context

**AC-1:** Every `regions[*]` in `cartography.yaml` has a non-empty `entities[]` array.

**AC-2:** Every entity with `tier=real_object` has a `binding` that resolves under the 54-3 validator's binding-resolution check.

**AC-3:** No entity has `tier=yes_and` (that tier is runtime-only).

**AC-4:** `pf validate locations tea_and_murder glenross` exits 0 with zero hard errors. Any remaining warnings are documented in the PR description (which tokens, why they're acceptable).

**AC-5:** Manual smoke: launch `just up`, connect, advance to any glenross region — the existing prose renders unchanged. The new `Location` tab (once 54-9 lands) shows the typed manifest server-side without affecting prose presentation.

**AC-6:** The legacy `landmarks[]` field on each region is left intact for backward compatibility (54-2's loader keeps the dual-field shape; eventual removal is a separate ticket).
