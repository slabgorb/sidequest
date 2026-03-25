# Epic 1: Rust Workspace Foundation

## Overview

Port the Python SideQuest game engine to Rust across a 5-crate workspace. Each story
delivers complete, tested, working code for its layer — not stubs. The architecture is
already proven: 30 ADRs were written for and validated against the running Python
application. This is a translation of known-good designs into Rust, with accumulated
Python technical debt cleaned up along the way.

Primary goal: deep Rust fluency through a real async game engine.
Secondary goal: shed the debt that Python's looseness allowed to accumulate.

## Background

SideQuest is an AI Narrator engine where Claude CLI subprocesses drive story progression.
The Python backend (sq-2) has been running successfully with:
- aiohttp WebSocket server → porting to axum
- Pydantic data models (~50+ models) → porting to serde derive structs
- YAML genre packs (7 packs, 174 YAML files) → porting to serde_yaml
- Claude CLI subprocess orchestration → porting to tokio::process
- Attention-zone prompt composer → porting faithfully (proven design)

The 30 ADRs in `docs/adr/` are not proposals — they document the designs that built the
working Python app. The Rust port implements the same designs with Rust idioms.

A technical debt audit (`docs/port-lessons.md`) identified 17 issues. The critical ones:
- **Server/Orchestrator coupling** (35+ direct state accesses) → enforce facade boundary
- **JSON extraction duplicated 4x** → single implementation
- **3 different Claude subprocess patterns** → single ClaudeClient
- **GameState god object** (255-line apply_patch) → domain-decomposed structs
- **Duplicate enums with conflicting thresholds** → single Disposition newtype
- **HP clamping bug** (missing floor in progression.py) → single clamp_hp function

## Technical Architecture

### Workspace Layout (5 crates, bottom-up dependency)

```
sidequest-api/
├── Cargo.toml              # [workspace] root
├── crates/
│   ├── sidequest-protocol/  # Layer 0: GameMessage enum, typed payloads (serde)
│   ├── sidequest-genre/     # Layer 1: YAML genre pack loader (serde_yaml)
│   ├── sidequest-game/      # Layer 2: Game state, characters, combat, chase
│   ├── sidequest-agents/    # Layer 3: Claude CLI subprocess, prompt composer
│   └── sidequest-server/    # Layer 4: axum HTTP/WebSocket, sessions
└── tests/                   # Integration tests
```

**Dependency graph (acyclic):**
- protocol depends on nothing
- genre depends on protocol
- game depends on protocol + genre
- agents depends on protocol + game
- server depends on all four

### Python → Rust Crate Mapping

| Python Module | Rust Crate |
|---|---|
| `server/protocol.py` | sidequest-protocol |
| `genre/models.py`, `genre/loader.py`, `genre/resolve.py`, `scenario/` | sidequest-genre |
| `game/state.py`, `game/character.py`, `game/npc.py`, `game/item.py`, `game/combat_models.py`, `game/chase.py`, `game/progression.py`, `game/turn_manager.py`, `game/state_delta.py`, `game/narrative_*.py`, `game/session.py`, `game/persistence.py` | sidequest-game |
| `agents/claude_agent.py`, `agents/narrator.py`, `agents/combat.py`, `agents/npc.py`, `agents/world_state.py`, `agents/intent_router.py`, `orchestrator.py`, `prompt_composer.py`, `prompt_builder.py` | sidequest-agents |
| `server/app.py`, `server/session_handler.py`, `server/cli.py` | sidequest-server |
| `comms/sanitize.py` | sidequest-protocol (input sanitization) |
| `lore/` | sidequest-game (state query mechanism) |
| `slash_commands/` | sidequest-server (request handlers) |
| `procgen/` | sidequest-game (name generation) |

### Key Technology Choices (from docs/tech-stack.md)

| Concern | Crate | Replaces |
|---------|-------|----------|
| Async runtime | tokio 1 (full) | asyncio |
| HTTP/WS | axum 0.8 | aiohttp |
| Serialization | serde 1 (derive) | Pydantic |
| YAML | serde_yaml 0.9 | PyYAML |
| Errors | thiserror 2 | Python exceptions |
| Logging | tracing 0.1 | logging module |
| IDs | uuid 1 (v4, serde) | uuid4() |
| SQLite | rusqlite 0.32 | json file I/O |

### Patterns to Establish

1. **Typed protocol** — `#[serde(tag = "type")]` enum for GameMessage
2. **Structured logging** — `tracing` spans with component/operation/player_id
3. **Newtype validation** — `Disposition(i8)`, `NonBlankString` — validate at construction
4. **Domain separation** — each crate owns its mutations behind a typed interface
5. **Deny unknown fields** — `#[serde(deny_unknown_fields)]` to catch YAML typos
6. **Attention-zone prompts** — primacy/early/valley/late/recency ordering (proven in Python)
7. **Service facade** — server talks to a trait, never to game internals directly
8. **Two-phase loading** — YAML → typed structs, then explicit cross-reference validation

### Port Principles

- **The ADRs are proven.** They built the working Python app. Port the design, not just the code.
- **Don't port the debt.** When Python has duplication or coupling, the Rust version is clean.
- **Let Rust enforce what Python couldn't.** Types, borrows, and exhaustive matches replace runtime checks.
- **SOUL.md is runtime data.** The prompt composer loads it from disk and injects it into agent prompts. It is not documentation.

## Planning Documents

| Document | Purpose |
|----------|---------|
| `docs/api-contract.md` | WebSocket + REST protocol spec (from UI) |
| `docs/tech-stack.md` | Crate choices and workspace layout |
| `docs/architecture.md` | System design, layers, implementation phases |
| `docs/port-lessons.md` | Python debt audit — what to fix in the port |
| `docs/SOUL.md` | Agent guidelines — runtime data for prompt composition |
| `docs/adr/` | 30 Architecture Decision Records (battle-tested) |

## Cross-Epic Dependencies

This epic must complete before any gameplay epics can begin. The genre pack YAML files
live in the Python repo (`sq-2/genre_packs/`). The API server takes a `--genre-packs-path`
argument at runtime. Test fixtures should use `mutant_wasteland/flickering_reach` (the
fully-spoilable pack).
