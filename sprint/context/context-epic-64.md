# Epic 64: Content Schema Compliance — Close Pack Validator Gaps

## Overview

Make every live genre pack pass validation cleanly, then make the validator
itself trustworthy. The epic began as a structural cleanup (missing world
files, undeclared extensions) and expanded — once the structural gaps closed,
review revealed the validator only checks *file existence*, never *file
contents*. The remaining stories harden the validator into a real schema +
cross-reference checker and fix a pre-existing import cycle that blocks the
dungeon test suite from running in isolation.

**Priority:** P2
**Repo:** content, server
**Stories:** 6 (14 points) — 64-1/2/3 complete, 64-4/5/6 added post-review

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **Pack schema** (`sidequest-content/pack_schema.yaml`) | `genre_pack.required_files`, `world.required_files`, `extensions` maps — the authority for what files a pack/world must have |
| **Pack validator** (`sidequest-server/sidequest/cli/validate/pack.py`) | `validate_pack_structure`, `_check_required_files`, `_validate_world` — the existence-only checker being extended |
| **Genre loader** (`sidequest-server/sidequest/genre/loader.py`) | `_load_single_world` (l.779-907), `load_genre_pack` — the real pydantic-backed load path the validator should reuse |
| **Server CLAUDE.md** | "No Silent Fallbacks", "No Source-Text Wiring Tests" — constrains how 64-4/64-6 may be implemented |

## Background

The genre-pack filesystem schema (`pack_schema.yaml`) landed and `pf validate
pack` / `just content-validate-all` were wired to enforce it. The first pass
surfaced two ERROR categories, both closed in 64-1 and 64-2:

- **Missing world-level required files** (5 worlds): `tropes.yaml`,
  `archetypes.yaml`, `portrait_manifest.yaml`.
- **Undeclared pack extensions** (5 packs): `pack.yaml` declared an extension
  whose backing file was absent. Resolved by either authoring the file
  (`archetype_constraints.yaml`, `projection.yaml`) or dropping the unused
  extension (`achievements`, pack-level `calendar`).

After those landed, all 10 live packs pass with zero errors. **But the review
that closed 64-1/64-2 exposed a deeper gap:** the validator is purely
structural. `pack.py` calls `is_file()` / `is_dir()` and resolves extension
backing files, but never parses a single file's contents — there is not one
`model_validate` call in it. A `tropes.yaml` with the wrong fields, or
outright garbage YAML, passes as long as the path exists. Proving the 7 new
world files in 64-1 actually loaded required hand-running them through the
pydantic models *separately* from the validator. That manual step is exactly
what 64-4 and 64-5 should make automatic.

64-6 captures a pre-existing bug surfaced during the same review: a circular
import between `session_handler.py` and `websocket_session_handler.py` makes
`tests/dungeon/test_region_projection_wiring.py::test_dungeon_map_frame_is_emitted_to_ui`
fail when run in isolation. It is unrelated to content but blocks the dungeon
suite (where 64-3's fixture work lives) and sits on the import path 64-4 will
need when it pulls in the loader graph.

## Technical Architecture

The validator and the runtime loader are currently **two separate code paths**
that should converge for content checks:

```
pack_schema.yaml ──► validate/pack.py        (existence only — today)
                         │
                         └─(64-4)─► reuse ──► genre/loader.py models
                                              NpcArchetype, TropeDefinition,
                                              PortraitManifestEntry,
                                              ArchetypeConstraints,
                                              DungeonTheme palette,
                                              projection rules
                         │
                         └─(64-5)─► cross-ref lint ──► rules.yaml allowed_*,
                                              resolved trope ids,
                                              jungian×role canonical sets,
                                              adjacency closure
```

**Key files:**

| File | Role | Touched by |
|------|------|-----------|
| `sidequest-server/sidequest/cli/validate/pack.py` | The validator; `validate_pack_structure` + per-world checks | 64-4, 64-5 |
| `sidequest-server/sidequest/cli/validate/common.py` | `packs_in` helper | 64-4 (read) |
| `sidequest-server/sidequest/genre/loader.py` | Real pydantic load path to reuse, not reimplement | 64-4 |
| `sidequest-server/sidequest/genre/models/*` | `character.NpcArchetype`, `tropes.TropeDefinition`, `pack.PortraitManifestEntry`, `archetype_constraints.ArchetypeConstraints` | 64-4, 64-5 |
| `sidequest-server/sidequest/dungeon/themes.py` | `load_theme_palette` (already enforces adjacency closure) | 64-5 (surface in validator) |
| `sidequest-server/sidequest/server/session_handler.py` (l.640) | Back-compat re-export — one half of the cycle | 64-6 |
| `sidequest-server/sidequest/server/websocket_session_handler.py` (l.144) | Imports `_SessionData`/`_State` back from session_handler — other half | 64-6 |

**Design constraint (from server CLAUDE.md):** the existing model classes are
the authority — reuse them via `model_validate`, do not copy field lists into
the validator. The `world.yaml` YAMLError currently swallowed at
`pack.py:203-204` is a No-Silent-Fallback violation and must be reported, not
`pass`ed.

## Cross-Epic Dependencies

**Depends on:**
- The landed `pack_schema.yaml` + `validate/pack.py` structural validator (this epic's own 64-1/64-2 work).

**Internal ordering:**
- 64-6 (break import cycle) should land before 64-4 if 64-4's content-validation pass imports the loader graph that transitively pulls `session_handler`/`websocket_session_handler`.
- 64-5 (cross-reference lint) builds on 64-4 (file contents must parse before their cross-references can be checked).

**Depended on by:**
- Future genre-pack and world authoring — a content-aware validator turns "the file exists" into "the file loads and is internally consistent", catching authoring errors at `just content-validate-all` instead of at runtime.
