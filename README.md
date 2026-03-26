# SideQuest — Rust Rewrite

Orchestrator repo for the SideQuest AI Narrator rewrite from Python to Rust.

SideQuest is an AI dungeon master that runs tabletop-style RPGs in any genre,
powered by coordinated Claude agents. This repo coordinates three subrepos and
holds the shared design artifacts.

## Repos

| Repo | Language | Purpose |
|------|----------|---------|
| **sidequest-api** | Rust | Game engine, WebSocket API, agent orchestration |
| **sidequest-ui** | TypeScript | React game client |
| **sidequest-daemon** | Python | Media services (image gen, TTS, audio) |

Subrepos are gitignored — clone them alongside this directory or use `just setup`.

## Quick Start

```bash
just setup        # Clone subrepos, install dependencies
just api-test     # Run Rust tests
just ui-dev       # Start React dev server
just daemon-run   # Start Python media daemon
just check-all    # Lint + test across all repos
just status       # Git status across all 4 repos
```

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — 7-layer system design
- [`docs/api-contract.md`](docs/api-contract.md) — WebSocket + REST protocol (23 message types)
- [`docs/tech-stack.md`](docs/tech-stack.md) — Crate and dependency choices
- [`docs/SOUL.md`](docs/SOUL.md) — 10 narrative design principles
- [`docs/gap-analysis-rust-port.md`](docs/gap-analysis-rust-port.md) — Feature parity roadmap
- [`docs/port-lessons.md`](docs/port-lessons.md) — Technical debt fixes from Python
- [`docs/adr/`](docs/adr/) — 31 Architecture Decision Records

## Genre Packs

YAML directories in `genre_packs/` define narrative worlds. Each pack can include
lore, rules, character creation scenes, tropes, audio, visual style, and more.
Shared across all three repos.

## Sprint Tracking

Sprint plans live in `sprint/` as YAML files with per-story context documents.
See `sprint/current-sprint.yaml` for active work.
