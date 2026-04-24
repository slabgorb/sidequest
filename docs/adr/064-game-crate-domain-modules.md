---
id: 64
title: "Game Crate Domain Modules — Organize 69 Flat Files"
status: accepted
date: 2026-04-04
deciders: [Keith]
supersedes: []
superseded-by: null
related: [60, 61]
tags: [codebase-decomposition]
implementation-status: live
implementation-pointer: null
---

# ADR-064: Game Crate Domain Modules — Organize 69 Flat Files

> **Status amendment (2026-04-23):** The Python port landed with `sidequest-server/sidequest/game/`
> keeping most files flat at package root rather than fully splitting into domain
> subdirectories — `projection/` is the one domain that did grow to directory
> scope. The flatter layout reflects deliberate application of the original ADR's
> anti-overnesting guidance. Future growth may promote additional domains into
> subdirectories. See the Post-port mapping section at the end.

## Context

`sidequest-game/src/` contains 69 `.rs` files in a completely flat directory
structure — no subdirectories, no module hierarchy. This is the largest crate in
the workspace (25,178 lines across source files) and spans at least eight game
subsystems:

| Domain | Files | Combined LOC |
|--------|-------|-------------|
| **Narrative** | lore.rs, conlang.rs, subject.rs, prerender.rs, render_queue.rs, commands.rs | ~5,900 |
| **Combat/Confrontation** | combat.rs, chase_depth.rs, encounter.rs, barrier.rs, accusation.rs | ~3,600 |
| **World** | world_materialization.rs, npc.rs, merchant.rs, monster_manual.rs | ~2,250 |
| **State** | state.rs, persistence.rs, builder.rs, multiplayer.rs | ~3,400 |
| **Economy** | inventory.rs, affinity.rs | ~1,260 |
| **Music/Audio** | music_director.rs, tension_tracker.rs | ~1,760 |
| **Character** | trope.rs + various small files | ~800+ |
| **Misc/Infra** | lib.rs, errors, tts_stream, etc. | ~1,500+ |

With 69 files flat in `src/`, Rust's visibility system provides no encapsulation.
Every type is `pub(crate)` accessible to every other file. There are no internal API
boundaries — `combat.rs` can reach into `music_director.rs` internals without
any module gate.

## Decision

**Introduce domain subdirectories under `sidequest-game/src/` to create module
boundaries and visibility control.**

### Module Structure

```
sidequest-game/src/
├── lib.rs              # Crate root — mod declarations, re-exports
├── narrative/
│   ├── mod.rs          # Public API for narrative subsystem
│   ├── lore/           # (per ADR-061) types, seeding, prompt, accumulate, language
│   ├── conlang.rs      # Constructed language generation
│   ├── subject.rs      # Subject extraction from narration
│   ├── prerender.rs    # Pre-rendered narrative segments
│   ├── render_queue.rs # Narration rendering pipeline
│   └── commands.rs     # Player command parsing
├── confrontation/
│   ├── mod.rs          # Public API for confrontation subsystem
│   ├── combat.rs       # Turn-based combat resolution
│   ├── chase.rs        # Chase sequences (was chase_depth.rs)
│   ├── encounter.rs    # Encounter generation and management
│   ├── barrier.rs      # Barrier/gate challenges
│   └── accusation.rs   # Mystery accusation mechanics
├── world/
│   ├── mod.rs          # Public API for world subsystem
│   ├── materialization.rs  # World generation (was world_materialization.rs)
│   ├── npc.rs          # NPC registry and management
│   ├── merchant.rs     # Trade and merchant systems
│   └── monster_manual.rs   # Pre-generated creature/NPC pools
├── state/
│   ├── mod.rs          # Public API for state subsystem
│   ├── game_state.rs   # GameState and mutations (was state.rs)
│   ├── persistence.rs  # SQLite save/load
│   ├── builder.rs      # State construction and initialization
│   └── multiplayer.rs  # Multi-player state synchronization
├── economy/
│   ├── mod.rs
│   ├── inventory.rs    # Item management
│   └── affinity.rs     # Faction/NPC relationship tracking
├── audio/
│   ├── mod.rs
│   ├── music_director.rs   # Track selection and cue management
│   └── tension_tracker.rs  # Drama/tension-driven music shifts
├── character/
│   ├── mod.rs
│   └── trope.rs        # Trope engine — tick, match, activate
└── (remaining infra files stay at root: lib.rs, errors.rs, tts_stream.rs, etc.)
```

### Visibility Strategy

Each domain's `mod.rs` explicitly exports its public API:

```rust
// confrontation/mod.rs
mod combat;
mod chase;
mod encounter;
mod barrier;
mod accusation;

pub use combat::{CombatState, resolve_combat_round};
pub use chase::{ChaseState, ChaseOutcome};
// ... explicit exports only
```

Types and functions NOT re-exported become `pub(super)` or private — invisible to
other domains. This is the key win: `combat.rs` internals are no longer reachable
from `music_director.rs`.

### Migration Strategy

1. **Start with the cleanest domain** — `confrontation/` has the most self-contained
   files with the fewest cross-domain imports.
2. **One domain at a time.** Move files, add `mod.rs`, update imports in `lib.rs`.
   Run `cargo check` after each domain.
3. **Preserve crate public API.** `lib.rs` re-exports domain public APIs so
   downstream crates (`sidequest-server`, `sidequest-agents`) see no change.
4. **Fix visibility violations as they surface.** When `cargo check` fails because
   module A reached into module B's internals, that's a real coupling to evaluate:
   either add it to B's public API or refactor the dependency.

### What Stays at Root

Infrastructure files that don't belong to a game domain:
- `lib.rs` — crate root
- `errors.rs` — shared error types
- `tts_stream.rs` — TTS trait definition
- Any other cross-cutting concerns

## Alternatives Considered

### Split into multiple crates
Would enforce the strongest boundaries but adds workspace complexity (more
`Cargo.toml` files, slower compilation due to crate graph, cross-crate trait
coherence issues). Module directories achieve 80% of the encapsulation benefit
at 20% of the cost. If a domain later needs to be shared independently (e.g.,
`sidequest-combat` as a standalone crate), the module structure makes that
extraction trivial. Rejected for now.

### Alphabetical grouping (a-g, h-n, o-z)
Arbitrary splitting reduces file count per directory but provides no semantic
value. The whole point is domain boundaries. Rejected.

### Keep flat, add visibility annotations only
`pub(crate)` vs `pub(super)` on individual items is theoretically possible but
impractical at 69 files — you'd need to annotate hundreds of items. Module
boundaries are the idiomatic Rust approach. Rejected.

## Consequences

- **Positive:** Visibility boundaries enforce domain separation. Internal refactors
  within `confrontation/` can't break `narrative/`.
- **Positive:** New files have an obvious home. Adding a puzzle system? Create
  `confrontation/puzzle.rs` or a new `puzzle/` domain.
- **Positive:** Code navigation improves dramatically — 69 flat files becomes
  7 domain directories averaging 4-5 files each.
- **Negative:** Significant one-time migration. Mitigate by doing one domain at a
  time across multiple stories.
- **Negative:** Some cross-domain coupling will surface as compile errors during
  migration. These are real architectural issues being made visible, not problems
  created by the refactor.
- **Risk:** Over-nesting. If a domain has only 1-2 files, keep it flat at root
  rather than creating a directory for one file.

## Post-port mapping (ADR-082)

The game-crate domain split carried to `sidequest-server/sidequest/game/`,
where each domain is a flat module at package root (not a subdirectory). Notable
submodules: `projection/` (field projection with predicate rules), which is the
one domain that did grow to directory scope.

The over-nesting risk called out in the original ADR held up — no domain with
1-2 files was given its own subdirectory during the port. The Python tree is
flatter than the decomposition originally envisioned, which is correct.
