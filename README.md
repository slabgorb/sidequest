# SideQuest — AI Dungeon Master

An AI narrator that runs tabletop-style RPGs in any genre, powered by coordinated
Claude agents. Players connect via browser, create characters through genre-driven
scenes, and explore procedural worlds with real-time image generation, voice synthesis,
and adaptive music.

## Repository Ecosystem

```
┌──────────────────────────────────────────────────────────────┐
│  oq-1 (this repo) — Orchestrator                            │
│  Sprint tracking, cross-repo justfile, architecture docs     │
└──────┬──────────────┬──────────────┬──────────────┬──────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────┐ ┌───────────┐ ┌──────────────┐ ┌────────────────┐
│sidequest-api│ │sidequest- │ │sidequest-    │ │sidequest-      │
│   (Rust)    │ │  ui (TS)  │ │daemon (Py)   │ │content (LFS)   │
│             │ │           │ │              │ │                │
│ Game engine │ │ React     │ │ Flux images  │ │ Genre pack     │
│ 7 Claude    │ │ client    │ │ Kokoro TTS   │ │ YAML + audio   │
│ agents      │ │ Audio     │ │ ACE-Step     │ │ + images       │
│ WebSocket   │ │ engine    │ │ music        │ │ (Git LFS)      │
│ server      │ │ Voice     │ │ 3-channel    │ │                │
│ SQLite      │ │ chat      │ │ mixer        │ │ 7 genre packs  │
└─────────────┘ └───────────┘ └──────────────┘ └────────────────┘
       ▲              │              ▲
       │  WebSocket   │   Unix sock  │
       └──────────────┘──────────────┘
```

| Repo | Language | Purpose | GitHub |
|------|----------|---------|--------|
| **oq-1** | — | Orchestrator, docs, sprint tracking | slabgorb/oq-1 |
| **sidequest-api** | Rust | Game engine, WebSocket API, agent orchestration | slabgorb/sidequest-api |
| **sidequest-ui** | TypeScript | React 19 game client, audio engine, WebRTC voice | slabgorb/sidequest-ui |
| **sidequest-daemon** | Python | Media services (Flux, Kokoro, ACE-Step, mixer) | slabgorb/sidequest-daemon |
| **sidequest-content** | YAML + LFS | Genre pack configs, audio, images, worlds | slabgorb/sidequest-content |

Subrepos are gitignored — clone them alongside this directory or use `just setup`.

## Quick Start

```bash
just setup          # Clone subrepos, install dependencies
just api-run        # Start Rust API server
just daemon-run     # Start Python media daemon
just ui-dev         # Start React dev server
just check-all      # Lint + test across all repos
just status         # Git status across all repos
```

### Running a Playtest

```bash
# Terminal 1: API server
just api-run

# Terminal 2: Media daemon (needs GPU for image/voice/music)
just daemon-run

# Terminal 3: React client
just ui-dev

# Open http://localhost:5173 in browser
# Select genre → world → enter name → create character → play
```

See [`docs/playtest-script.md`](docs/playtest-script.md) for a structured test checklist.

## Genre Packs

Seven narrative worlds, each with its own rules, tropes, character creation, audio, and visual style:

| Pack | Theme | Worlds |
|------|-------|--------|
| **elemental_harmony** | Martial arts / elemental magic | Shattered Accord, Burning Peace |
| **low_fantasy** | Gritty medieval | — |
| **mutant_wasteland** | Post-apocalyptic mutants | Flickering Reach |
| **neon_dystopia** | Cyberpunk | — |
| **pulp_noir** | 1930s detective | — |
| **road_warrior** | Vehicular post-apocalypse | — |
| **space_opera** | Sci-fi space adventure | — |

Genre packs live in `sidequest-content/` (Git LFS) and are loaded by path reference.

## How It Works

1. **Player connects** via WebSocket from the React client
2. **Character creation** flows through genre-driven scenes (choices + freeform text)
3. **Each turn:** player action → intent classification (Haiku) → agent dispatch (Narrator/WorldBuilder/Ensemble/etc.) → state patch → narration broadcast
4. **Media pipeline:** narration triggers image generation (Flux), voice synthesis (Kokoro), and mood-based music (ACE-Step) in parallel
5. **Trope engine** drives narrative arcs — escalation beats fire as tropes progress
6. **Multiplayer** supports turn barriers, perception rewriting, and WebRTC voice chat

All LLM calls use `claude -p` subprocess — no SDK dependency.

## Documentation

### System Design
- [`docs/system-diagram.md`](docs/system-diagram.md) — Repository ecosystem, data flow, sequence diagrams
- [`docs/architecture.md`](docs/architecture.md) — 7-layer system design
- [`docs/api-contract.md`](docs/api-contract.md) — WebSocket + REST protocol
- [`docs/tech-stack.md`](docs/tech-stack.md) — Crate and dependency choices

### Game Design
- [`docs/SOUL.md`](docs/SOUL.md) — 10 narrative design principles
- [`docs/adr/`](docs/adr/) — 32 Architecture Decision Records

### Project Status
- [`docs/feature-inventory.md`](docs/feature-inventory.md) — Features: done, wired, planned
- [`docs/playtest-script.md`](docs/playtest-script.md) — Structured playtest checklist
- [`docs/gap-analysis-rust-port.md`](docs/gap-analysis-rust-port.md) — Feature parity roadmap
- [`docs/port-lessons.md`](docs/port-lessons.md) — Technical debt fixes from Python
- [`docs/wiring-audit.md`](docs/wiring-audit.md) — Signal-path mapping with Mermaid diagrams

## Progress

59 of 108 stories complete across 11 epics (55%).

| Epic | Status | Description |
|------|--------|-------------|
| 1. Workspace Scaffolding | **Complete** | Rust crates, types, genre loading |
| 2. Core Game Loop | **Complete** | Turn loop, agents, persistence |
| 3. Game Watcher | **Complete** | Telemetry, GM mode |
| 4. Media Integration | **Complete** | Images, TTS, music, audio mixing |
| 5. Pacing & Drama | 40% | Tension model, drama-aware delivery |
| 6. Active World | 33% | Scene directives, faction agendas |
| 7. Scenario System | 0% | Whodunit, belief state, gossip |
| 8. Multiplayer | 89% | Turn barrier, perception rewriter |
| 9. Character Depth | 10% | Abilities, slash commands |
| 10. OCEAN Personality | 0% | Big Five NPC profiles |
| 11. Lore & Language | 0% | RAG retrieval, conlang names |

## Sprint Tracking

Sprint plans live in `sprint/` as YAML files with per-story context documents.
See `sprint/current-sprint.yaml` for active work.
