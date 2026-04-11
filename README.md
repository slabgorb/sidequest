# SideQuest — AI Dungeon Master

An AI narrator engine that runs tabletop-style RPGs in any genre, powered by a coordinated
Claude narrator. Players connect via browser, create characters through genre-driven
scenes, and explore procedural worlds with real-time image generation and adaptive music.
Multiplayer with turn barriers, perception rewriting, and sealed-letter turn coordination.

## Repository Ecosystem

```
┌──────────────────────────────────────────────────────────────┐
│  orc-quest (this repo) — Orchestrator                       │
│  Sprint tracking, cross-repo justfile, architecture docs     │
└──────┬──────────────┬──────────────┬──────────────┬──────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────┐ ┌───────────┐ ┌──────────────┐ ┌────────────────┐
│sidequest-api│ │sidequest- │ │sidequest-    │ │sidequest-      │
│   (Rust)    │ │  ui (TS)  │ │daemon (Py)   │ │content         │
│             │ │           │ │              │ │                │
│ 12-crate    │ │ React 19  │ │ Flux image   │ │ Genre pack     │
│ workspace   │ │ client    │ │ renderer     │ │ YAML + audio   │
│ Narrator    │ │ Audio     │ │ ACE-Step     │ │ + images       │
│ agent       │ │ engine    │ │ music        │ │                │
│ ~70 game    │ │ 3D dice   │ │ Music + SFX  │ │                │
│ modules     │ │ renderer  │ │ mixer        │ │ 11 genre packs │
└─────────────┘ └───────────┘ └──────────────┘ └────────────────┘
       ▲              │              ▲
       │  WebSocket   │   Unix sock  │
       └──────────────┘──────────────┘
```

| Repo | Language | Purpose | GitHub |
|------|----------|---------|--------|
| **orc-quest** | — | Orchestrator, docs, sprint tracking | slabgorb/orc-quest |
| **sidequest-api** | Rust | Game engine, WebSocket API, agent orchestration | slabgorb/sidequest-api |
| **sidequest-ui** | TypeScript | React 19 game client, audio engine, 3D dice overlay | slabgorb/sidequest-ui |
| **sidequest-daemon** | Python | Media services (Flux image gen, ACE-Step music, SFX mixer) | slabgorb/sidequest-daemon |
| **sidequest-content** | YAML | Genre pack configs, audio, images, worlds | slabgorb/sidequest-content |

Subrepos are gitignored — clone them alongside this directory or use `just setup`.

## Quick Start

```bash
just setup          # Clone subrepos, install dependencies
just api-run        # Start Rust API server
just daemon-run     # Start Python media daemon
just ui-dev         # Start React dev server
just api-check      # fmt + clippy + test (API)
just status         # Git status across all repos
```

### Running a Playtest

```bash
# Terminal 1: API server
just api-run

# Terminal 2: Media daemon (needs GPU for image/music generation)
just daemon-run

# Terminal 3: React client
just ui-dev

# Open http://localhost:5173 in browser
# Select genre → world → enter name → create character → play
```

See [`docs/playtest-script.md`](docs/playtest-script.md) for a structured test checklist.

## Genre Packs

Eleven narrative worlds, each with its own rules, tropes, character creation, audio, visual style, faction agendas, OCEAN personality archetypes, and conlang morphemes:

| Pack | Theme |
|------|-------|
| **caverns_and_claudes** | High fantasy dungeon crawl |
| **elemental_harmony** | Martial arts / elemental magic |
| **low_fantasy** | Gritty medieval |
| **mutant_wasteland** | Post-apocalyptic mutants |
| **neon_dystopia** | Cyberpunk |
| **pulp_noir** | 1930s detective |
| **road_warrior** | Vehicular post-apocalypse |
| **space_opera** | Sci-fi space adventure |
| **spaghetti_western** | Dusty frontier / outlaw west |
| **star_chamber** | Renaissance court intrigue |
| **victoria** | Gaslamp Victorian |

Genre packs live in `sidequest-content/` and are loaded by path reference.

## How It Works

1. **Player connects** via WebSocket from the React client
2. **Character creation** flows through genre-driven scenes (choices + freeform text)
3. **Each turn:** player action → narrator dispatch → state patch → narration broadcast
4. **Unified narrator** (per ADR-067) handles all intents via a persistent Opus session; auxiliary agents (world_builder, troper, resonator) run for specialist tasks, all via `claude -p` subprocess
5. **Media pipeline:** narration triggers image generation (Flux) and mood-based music (ACE-Step) in parallel — background-first, only text is critical path
6. **Pacing engine:** dual-track TensionTracker produces drama_weight (0.0-1.0) → controls narration length, delivery speed, beat escalation, and media render gating
7. **World systems:** faction agendas inject per-turn, trope engine drives narrative arcs, world materialization tracks campaign maturity
8. **NPC personality:** OCEAN Big Five profiles shape NPC dialogue and behavior, shift over time from game events
9. **Knowledge:** KnownFacts accumulate from play, lore fragments seed from genre packs, conlang names generated from morpheme glossaries
10. **Multiplayer:** turn barriers with adaptive timeout, 3 turn modes (FREE_PLAY/STRUCTURED/CINEMATIC), sealed-letter coordination, perception rewriting

## Rust Crate Architecture

```
sidequest-api/
├── sidequest-protocol       # GameMessage enum, typed payloads (serde)
├── sidequest-genre          # YAML genre pack loader
├── sidequest-game           # ~70 modules — state, combat, NPCs, lore, audio, pacing
├── sidequest-agents         # Claude CLI subprocess, narrator + auxiliary agents
├── sidequest-server         # axum HTTP/WS, session management, orchestrator
├── sidequest-daemon-client  # HTTP/Unix-socket client for Python media daemon
├── sidequest-telemetry      # OTEL span definitions and watcher macros
├── sidequest-validate       # Genre pack validation utilities
├── sidequest-encountergen   # CLI: enemy stat block generator
├── sidequest-loadoutgen     # CLI: starting equipment generator
├── sidequest-namegen        # CLI: NPC identity block generator
└── sidequest-promptpreview  # CLI: prompt preview and inspection
```

See [`docs/architecture.md`](docs/architecture.md) for the full system design.

## Documentation

### System Design
- [`docs/architecture.md`](docs/architecture.md) — Layer diagram, crate structure, game systems
- [`docs/wiring-diagrams.md`](docs/wiring-diagrams.md) — End-to-end signal traces (Mermaid)
- [`docs/system-diagram.md`](docs/system-diagram.md) — Repository ecosystem, data flow, sequence diagrams
- [`docs/api-contract.md`](docs/api-contract.md) — WebSocket + REST protocol
- [`docs/tech-stack.md`](docs/tech-stack.md) — Crate and dependency choices

### Game Design
- [`docs/adr/`](docs/adr/) — Architecture Decision Records (see [`docs/adr/README.md`](docs/adr/README.md) for the index)
- [`docs/gm-handbook.md`](docs/gm-handbook.md) — GM handbook (Forge theory applied to SideQuest)

### Project Status
- [`docs/feature-inventory.md`](docs/feature-inventory.md) — Feature inventory: done, wired, planned
- [`docs/genre-pack-status.md`](docs/genre-pack-status.md) — Per-pack content completeness

## Sprint Tracking

Sprint plans live in `sprint/` as YAML files with per-story context documents.
See `sprint/current-sprint.yaml` for active work and `sprint/archive/` for completed stories.
