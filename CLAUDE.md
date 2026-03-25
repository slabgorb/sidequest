# CLAUDE.md — SideQuest (Rust Rewrite)

This is the orchestrator repo for the SideQuest Rust rewrite. It coordinates three subrepos:
- **sidequest-api** — Rust game engine and WebSocket API (workspace with 5 crates)
- **sidequest-ui** — React/TypeScript game client
- **sidequest-daemon** — Python media services (image gen, TTS, audio)

## CRITICAL: Personal Project

This is a personal project under the `slabgorb` GitHub account.
- **No Jira integration.** Never create, reference, or interact with Jira tickets.
- **No 1898 org.** Nothing goes to the work GitHub org. Ever.
- All repos live under `github.com/slabgorb/`.

## Project Overview

A port of the SideQuest AI Narrator engine from Python to Rust, with the frontend
split into its own repo. The original Python codebase (sq-2) continues to run
independently.

**Goal:** Learn Rust deeply by porting a real async game engine, while also
achieving a clean frontend/backend repo split.

## Repository Structure

```
orc-quest/                    # This repo (orchestrator)
├── genre_packs/              # YAML genre data (shared across all repos)
├── sprint/                   # Sprint tracking
├── docs/                     # Architecture docs and 30 ADRs
│   ├── api-contract.md       # WebSocket + REST contract (from UI)
│   ├── tech-stack.md         # Crate choices (aligned with axiathon)
│   ├── architecture.md       # System design and layer diagram
│   └── adr/                  # Architecture Decision Records
├── repos.yaml                # Multi-repo topology
└── justfile                  # Cross-repo task runner

sidequest-api/                # Rust backend (subrepo, gitignored)
├── Cargo.toml                # [workspace] root
├── crates/
│   ├── sidequest-protocol/   # GameMessage, typed payloads (serde)
│   ├── sidequest-genre/      # YAML genre pack loader
│   ├── sidequest-game/       # State, characters, combat, chase, tropes
│   ├── sidequest-agents/     # Claude CLI subprocess orchestration
│   └── sidequest-server/     # axum HTTP/WebSocket, sessions
└── tests/

sidequest-ui/                 # React frontend (subrepo, gitignored)
├── src/
│   ├── components/
│   ├── providers/
│   └── screens/
└── package.json

sidequest-daemon/             # Python media services (subrepo, gitignored)
├── renderer/                 # Flux/SDXL image generation
├── tts/                      # Kokoro + Piper voice synthesis
├── audio/                    # Library playback, theme rotation
├── scene/                    # Scene interpreter, subject extractor
└── pyproject.toml
```

## Architecture

- **API communicates via WebSocket** for real-time game events (narration, state updates)
- **Small REST surface** for save/load, character listing, genre pack metadata
- **Claude CLI (`claude -p`)** for all LLM calls — subprocess, not SDK
- **Genre packs** are YAML, loaded by the API from a configured path
- **Media daemon** (`sidequest-daemon`) stays in Python as a sidecar for image/audio generation

## Commands

```bash
# From orchestrator root:
just api-test          # Run Rust tests
just api-build         # Build Rust backend
just api-run           # Run API server
just ui-dev            # Start React dev server
just ui-test           # Run frontend tests
just ui-build          # Build frontend
```

## Spoiler Protection

Same rules as sq-2. See sq-2/CLAUDE.md for the full policy.
- **Fully spoilable:** `mutant_wasteland/flickering_reach` only
- **Fully unspoiled:** Everything else
