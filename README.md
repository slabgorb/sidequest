# SideQuest — AI Dungeon Master

An AI narrator engine that runs tabletop-style RPGs in any genre, powered by a persistent
Claude narrator. Players connect via browser, create characters through genre-driven
scenes, and explore procedural worlds with real-time image generation and adaptive music.
Multiplayer with turn barriers, perception rewriting, and sealed-letter turn coordination.

## Repository Ecosystem

```
┌──────────────────────────────────────────────────────────────┐
│  orc-quest (this repo) — Orchestrator                        │
│  Sprint tracking, cross-repo justfile, architecture docs     │
└──────┬──────────────┬──────────────┬──────────────┬──────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌──────────────┐ ┌───────────┐ ┌──────────────┐ ┌────────────────┐
│sidequest-    │ │sidequest- │ │sidequest-    │ │sidequest-      │
│server (Py)   │ │  ui (TS)  │ │daemon (Py)   │ │content         │
│              │ │           │ │              │ │                │
│ FastAPI +    │ │ React 19  │ │ Z-Image /    │ │ Genre pack     │
│ uvicorn      │ │ client    │ │ Flux image   │ │ YAML + audio   │
│ WebSocket    │ │ Audio     │ │ renderer     │ │ + images       │
│ Narrator     │ │ engine    │ │ ACE-Step     │ │                │
│ subprocess   │ │ 3D dice   │ │ music + SFX  │ │ 8 genre packs  │
│ (claude -p)  │ │ overlay   │ │ mixer        │ │                │
└──────────────┘ └───────────┘ └──────────────┘ └────────────────┘
       ▲              │              ▲
       │  WebSocket   │   Unix sock  │
       └──────────────┴──────────────┘
```

| Repo | Language | Purpose | GitHub |
|------|----------|---------|--------|
| **orc-quest** | — | Orchestrator, docs, sprint tracking | slabgorb/orc-quest |
| **sidequest-server** | Python | Game engine, FastAPI WebSocket API, narrator orchestration | slabgorb/sidequest-server |
| **sidequest-ui** | TypeScript | React 19 client, audio engine, 3D dice overlay | slabgorb/sidequest-ui |
| **sidequest-daemon** | Python | Media services (Z-Image / Flux image gen, ACE-Step music, SFX mixer) | slabgorb/sidequest-daemon |
| **sidequest-content** | YAML | Genre pack configs, audio, images, worlds | slabgorb/sidequest-content |

> **Port history.** The backend was briefly a Rust workspace (`sidequest-api`, ~2026-03-30
> to 2026-04-19) before being ported back to Python as `sidequest-server` per
> [ADR-082](docs/adr/082-port-api-rust-to-python.md). The Rust tree is preserved
> read-only at <https://github.com/slabgorb/sidequest-api> for ADR archaeology only.

Subrepos are gitignored — clone them alongside this directory or use `just setup`.

## Quick Start

```bash
just setup          # Install deps for every subrepo (uv sync + npm install)
just up             # Boot daemon → server → client; tail merged logs
just down           # Stop all background services
just status         # Git status across every repo
just check-all      # server-check + client-lint + client-test + daemon-lint
```

### Running a Playtest

```bash
just up             # One command — boots daemon, server, and client in order
# or, in three terminals:
just daemon         # Media daemon (warmup; needs GPU for image/music gen)
just server         # FastAPI on :8765
just client         # Vite on :5173

# Open http://localhost:5173 in browser
# Select genre → world → enter name → create character → play
```

Logs tee to `/tmp/sidequest-{server,client,daemon}.log`. Use `just logs` to tail all of
them, or `just logs server` for one.

See [`docs/playtest-script.md`](docs/playtest-script.md) for a structured test checklist
and [`scenarios/`](scenarios/) for headless playtest YAML driven by `just playtest-scenario`.

## Genre Packs

Eight narrative worlds, each with its own rules, tropes, character creation, audio, visual
style, faction agendas, OCEAN personality archetypes, and conlang morphemes:

| Pack | Theme |
|------|-------|
| **caverns_and_claudes** | High fantasy dungeon crawl |
| **elemental_harmony** | Martial arts / elemental magic |
| **heavy_metal** | Apocalyptic metal opera |
| **mutant_wasteland** | Post-apocalyptic mutants |
| **space_opera** | Sci-fi space adventure |
| **spaghetti_western** | Dusty frontier / outlaw west |
| **victoria** | Brontë-flavored gaslamp gothic (social-first) |

Genre packs live in `sidequest-content/genre_packs/` and are loaded via the
`SIDEQUEST_GENRE_PACKS` env var. See
[`docs/genre-pack-status.md`](docs/genre-pack-status.md) for per-pack completeness.

## How It Works

1. **Player connects** via WebSocket from the React client
2. **Character creation** flows through genre-driven scenes (choices + freeform text)
3. **Each turn:** player action → narrator dispatch → state patch → narration broadcast
4. **Unified narrator** (per [ADR-067](docs/adr/067-unified-narrator-agent.md)) handles
   all intents via a persistent Opus session; auxiliary agents (world_builder, troper,
   resonator) run for specialist tasks, all via `claude -p` subprocess
   ([ADR-001](docs/adr/001-claude-cli-only.md))
5. **Media pipeline:** narration triggers image generation and mood-based music in
   parallel — background-first, only text is critical path
   ([ADR-005](docs/adr/005-background-first-pipeline.md))
6. **Pacing engine:** dual-track TensionTracker produces `drama_weight` (0.0–1.0) →
   controls narration length, delivery speed, beat escalation, and media render gating
7. **World systems:** faction agendas inject per-turn, trope engine drives narrative arcs,
   world materialization tracks campaign maturity
8. **NPC personality:** OCEAN Big Five profiles shape NPC dialogue and behavior, shifting
   over time from game events
9. **Knowledge:** KnownFacts accumulate from play, lore fragments seed from genre packs,
   conlang names generated from morpheme glossaries
   ([ADR-091](docs/adr/091-culture-corpus-markov-naming.md))
10. **Multiplayer:** turn barriers with adaptive timeout, three turn modes
    (FREE_PLAY / STRUCTURED / CINEMATIC), sealed-letter coordination, perception rewriting

## Server Module Layout

```
sidequest-server/sidequest/
├── protocol/         # GameMessage, typed payloads (pydantic)
├── server/           # FastAPI app, WebSocket, dispatch, sessions
├── handlers/         # Per-message-type dispatch handlers
├── agents/           # claude -p subprocess orchestration (narrator + auxiliaries)
├── game/             # State, characters, encounters, tropes, turns, persistence
├── genre/            # YAML genre pack loader
├── audio/            # Server-side music/SFX coordination
├── media/            # Image generation orchestration
├── magic/            # Magic system mechanics
├── interior/         # Interior/room state
├── orbital/          # Orbital / space-scene mechanics
├── corpus/           # Conlang corpus + Markov naming
├── renderer/         # Render scheduling + throttle
├── daemon_client/    # Unix-socket client for the media daemon
├── telemetry/        # OTEL span definitions and watcher hooks
└── cli/              # Standalone CLIs: encountergen, loadoutgen, namegen,
                      #   validate, corpusmine, corpuslabel, corpusdiff
```

See [`docs/architecture.md`](docs/architecture.md) for the full system design.

## Documentation

### System Design
- [`docs/architecture.md`](docs/architecture.md) — Layer diagram, module structure, game systems
- [`docs/wiring-diagrams.md`](docs/wiring-diagrams.md) — End-to-end signal traces (Mermaid)
- [`docs/system-diagram.md`](docs/system-diagram.md) — Repository ecosystem, data flow, sequence diagrams
- [`docs/api-contract.md`](docs/api-contract.md) — WebSocket + REST protocol
- [`docs/tech-stack.md`](docs/tech-stack.md) — Library and dependency choices

### Game Design
- [`docs/adr/`](docs/adr/) — Architecture Decision Records (see [`docs/adr/README.md`](docs/adr/README.md) for the index)
- [`docs/gm-handbook.md`](docs/gm-handbook.md) — GM handbook (Forge theory applied to SideQuest)

### Project Status
- [`docs/feature-inventory.md`](docs/feature-inventory.md) — Feature inventory: done, wired, planned
- [`docs/genre-pack-status.md`](docs/genre-pack-status.md) — Per-pack content completeness

## Sprint Tracking

Sprint plans live in `sprint/` as YAML files with per-story context documents.
See `sprint/current-sprint.yaml` for active work and `sprint/archive/` for completed stories.
