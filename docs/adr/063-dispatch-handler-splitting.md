---
id: 63
title: "Dispatch Handler Splitting — By Pipeline Stage"
status: accepted
date: 2026-04-04
deciders: [Keith]
supersedes: []
superseded-by: null
related: [58, 62]
tags: [codebase-decomposition]
implementation-status: live
implementation-pointer: null
---

# ADR-063: Dispatch Handler Splitting — By Pipeline Stage

> **Status amendment (2026-04-23):** Executed during the Python port (ADR-082).
> Dispatch lives as `sidequest-server/sidequest/server/dispatch/` (package),
> with per-stage modules (chargen_loadout.py, combat_brackets.py, confrontation.py,
> culture_context.py, encounter_lifecycle.py, opening_hook.py, scenario_bind.py,
> chargen_summary.py). See the Post-port mapping section at the end.

## Context

`sidequest-server/src/dispatch/mod.rs` is 2,132 lines with zero impl blocks — it's
a collection of large async functions forming the narration dispatch pipeline. The
current functions and their approximate sizes:

| Function | Lines | Responsibility |
|----------|-------|----------------|
| `handle_barrier()` | ~130 | Barrier/gate resolution before narration |
| `update_npc_registry()` | ~210 | NPC extraction and registry sync |
| `validate_continuity()` | ~46 | Post-narration continuity checks |
| `build_response_messages()` | ~200 | Convert narration result → GameMessages |
| `sync_locals_to_snapshot()` | ~54 | Sync local state changes to snapshot |
| `persist_game_state()` | ~120 | Save state to SQLite |
| `spawn_tts_pipeline()` | ~240 | TTS chunking and voice synthesis |
| `emit_telemetry()` | ~100 | OTEL span emission |
| `handle_aside()` | ~200 | Aside/whisper narration path |
| (remaining) | ~830 | Main dispatch orchestration, context building |

These are pipeline stages — they execute sequentially on every player action. The
file reads top-to-bottom as the dispatch pipeline, which is conceptually clean, but
2,132 lines in one file means any change to TTS, telemetry, or NPC handling requires
navigating the entire pipeline.

## Decision

**Split `dispatch/mod.rs` into stage-oriented submodules.**

### Module Structure

```
sidequest-server/src/dispatch/
├── mod.rs              # Main dispatch orchestration (~500 lines)
│                       #   DispatchContext, main dispatch fn, context building
├── connect.rs          # (already exists) — connection/session setup
├── barriers.rs         # handle_barrier() — pre-narration gate resolution
├── npc.rs              # update_npc_registry() — NPC extraction and sync
├── response.rs         # build_response_messages(), validate_continuity(),
│                       #   sync_locals_to_snapshot() — post-narration processing
├── persistence.rs      # persist_game_state() — SQLite save pipeline
├── tts.rs              # spawn_tts_pipeline() — voice synthesis orchestration
├── telemetry.rs        # emit_telemetry() — OTEL span construction
└── aside.rs            # handle_aside() — aside/whisper narration path
```

### Why Pipeline Stages, Not Arbitrary Size Chunks

The functions already form a natural pipeline: barrier → narrate → NPC sync →
response build → persist → TTS → telemetry. Splitting by pipeline stage means
each module has one job in the sequence. When TTS needs changes, you open `tts.rs`.
When telemetry needs a new span, you open `telemetry.rs`. No scrolling through
2,100 lines.

### DispatchContext Stays in mod.rs

`DispatchContext` is the pipeline's shared state — it threads through every stage.
Keeping it in `mod.rs` (the pipeline orchestrator) and passing `&mut DispatchContext`
to each stage function maintains the single-owner pattern without requiring the
context type to live in a separate module that everything imports.

## Alternatives Considered

### Keep as single file with better section comments
Already attempted (the file has section separators). At 2,132 lines, section comments
don't prevent the cognitive load of a 2K-line file or the merge conflicts when two
features touch different stages. Rejected.

### Split into separate traits per stage
Over-abstraction. These are pure functions that take a context and return results.
Trait objects would add vtable overhead and lose the clarity of direct function calls.
The pipeline is not polymorphic — there's one dispatch path. Rejected.

## Consequences

- **Positive:** `mod.rs` drops from 2,132 to ~500 lines (orchestration + context).
  Each stage module is 100-250 lines.
- **Positive:** Telemetry changes (frequent given the OTEL mandate) are isolated to
  `telemetry.rs`. TTS pipeline changes don't touch NPC registration.
- **Positive:** `aside.rs` extraction makes the aside path first-class rather than
  an afterthought at the bottom of the file.
- **Negative:** Pipeline reading requires jumping between files. Mitigated by `mod.rs`
  serving as the readable orchestration sequence with clear stage calls.

## Post-port mapping (ADR-082)

The dispatch-splitting decision is realized in Python as
`sidequest-server/sidequest/server/dispatch/` (a package, not a single module).
Each Rust pipeline stage became a sibling Python module:

- `chargen_loadout.py`, `chargen_summary.py` — character creation stages
- `combat_brackets.py`, `confrontation.py` — combat + confrontation engine hooks
- `culture_context.py` — culture/voice injection
- `encounter_lifecycle.py` — encounter state transitions
- `opening_hook.py` — session opener
- `scenario_bind.py` — scenario pack binding

The `mod.rs`-as-orchestration-sequence pattern translates to `__init__.py` plus
the top-level dispatch coordinator in `session_handler.py`. Aside handling is
first-class in the pipeline.
