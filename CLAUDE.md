# CLAUDE.md — SideQuest (Rust Rewrite)

This is the orchestrator repo for the SideQuest Rust rewrite. It coordinates four subrepos:
- **sidequest-api** — Rust game engine and WebSocket API (workspace with 6 crates)
- **sidequest-ui** — React/TypeScript game client
- **sidequest-daemon** — Python media services (image gen, TTS, audio)
- **sidequest-content** — Genre packs (YAML configs, audio, images, world data)

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
├── sprint/                   # Sprint tracking
├── docs/                     # Architecture docs and 35 ADRs
│   ├── api-contract.md       # WebSocket + REST contract (from UI)
│   ├── tech-stack.md         # Crate choices
│   ├── architecture.md       # System design and layer diagram
│   └── adr/                  # Architecture Decision Records
├── scripts/                  # Cross-repo scripts (playtest, music gen, etc.)
├── scenarios/                # Test/playtest scenarios
└── justfile                  # Cross-repo task runner

sidequest-content/            # Genre packs — single source of truth (subrepo)
├── genre_packs/
│   ├── elemental_harmony/
│   ├── low_fantasy/
│   ├── mutant_wasteland/
│   ├── neon_dystopia/
│   ├── pulp_noir/
│   ├── road_warrior/
│   ├── space_opera/
│   ├── spaghetti_western/
│   ├── victoria/
│   └── <genre>/worlds/<world>/
└── CLAUDE.md

sidequest-api/                # Rust backend (subrepo)
├── Cargo.toml                # [workspace] root
├── crates/
│   ├── sidequest-protocol/   # GameMessage, typed payloads (serde)
│   ├── sidequest-genre/      # YAML genre pack loader
│   ├── sidequest-game/       # State, characters, combat, chase, tropes
│   ├── sidequest-agents/     # Claude CLI subprocess orchestration
│   ├── sidequest-daemon-client/ # Client for Python media daemon
│   └── sidequest-server/     # axum HTTP/WebSocket, sessions
└── tests/

sidequest-ui/                 # React frontend (subrepo)
├── src/
│   ├── components/
│   ├── screens/
│   ├── providers/
│   ├── hooks/
│   ├── audio/
│   ├── types/
│   └── webrtc/
└── package.json

sidequest-daemon/             # Python media services (subrepo)
├── sidequest_daemon/         # Package root
├── tests/
└── pyproject.toml
```

## Architecture

- **API communicates via WebSocket** for real-time game events (narration, state updates)
- **Small REST surface** for save/load, character listing, genre pack metadata
- **Claude CLI (`claude -p`)** for all LLM calls — subprocess, not SDK
- **Genre packs** live in `sidequest-content/genre_packs/` (single source of truth), loaded by the API from a configured path
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

## Velocity & Quality Standards

### The Numbers

First commit: 2026-03-25. In 3.5 days:

| Repo | Commits | LOC | Language |
|------|---------|-----|----------|
| **sidequest-api** | 299 | 68,358 | Rust |
| **orc-quest** (orchestrator) | 164 | — | YAML/MD |
| **sidequest-ui** | 45 | 15,675 | TypeScript/React |
| **sidequest-content** | 9 | 33,059 | YAML |
| **sidequest-daemon** | 11 | 8,071 | Python |
| **Total** | **528** | **125,163** | |

672 of 726 story points delivered. 85 stories completed. 12 epics.

### What This Means for You

This velocity is real. We shipped a 5-crate Rust game engine, a React client,
a Python media daemon, 7 genre packs, 30 ADRs, and a full WebSocket protocol
in under 4 days. When you identify the correct fix, it takes minutes — the
item-acquisition rewrite (regex-on-prose to LLM-structured-extraction, touching
protocol types, orchestrator, narrator prompt, server wiring, and tests) took
5 minutes 38 seconds wall time.

**Do not underestimate what we can do.** There is no fix too ambitious, no
refactor too large, no "we should do this later." If the right fix takes 20
minutes and the hack takes 5, do the right fix — because the hack will cost
2-3x MORE when we come back to it. Not 20% more. Not 30% more. The debugging
cost of figuring out whether something is a stub or the real thing, whether a
regex hack is the intended behavior or a placeholder, whether `if false {` was
temporary or permanent — that confusion tax dwarfs the original implementation
time by an order of magnitude.

### Rules

- No stubs, no hacks, no "we'll fix it later" shortcuts
- No skipping tests to save time
- No half-wired features — connect the full pipeline or don't start
- If something needs 5 connections, make 5 connections. Don't ship 3 and call it done.
- **Never say "the right fix is X" and then do Y.** Do X.
- **Never downgrade to a "quick fix" because you think the context is "just a playtest."**
  Every playtest is production tomorrow. Fix it right.

## Development Principles

### No Silent Fallbacks
If something isn't where it should be, fail loudly. Never silently try an alternative
path, config, or default. Silent fallbacks mask configuration problems and lead to
hours of debugging "why isn't this quite right."

### No Stubbing
Don't create stub implementations, placeholder modules, or skeleton code. If a feature
isn't being implemented now, don't leave empty shells for it. Dead code is worse than
no code.

### Don't Reinvent — Wire Up What Exists
Before building anything new, check if the infrastructure already exists in the codebase.
Many systems are fully implemented but not wired into the server or UI. The fix is
integration, not reimplementation.

### Verify Wiring, Not Just Existence
When checking that something works, verify it's actually connected end-to-end. Tests
passing and files existing means nothing if the component isn't imported, the hook isn't
called, or the endpoint isn't hit in production code. Check that new code has non-test
consumers.

### Every Test Suite Needs a Wiring Test
Unit tests prove a component works in isolation. That's not enough. Every set of tests
must include at least one integration test that verifies the component is wired into the
system — imported, called, and reachable from production code paths.

### Rust vs Python Split
If it doesn't involve operating LLMs, it goes in Rust. If it needs to run model inference
(Flux, Kokoro, ACE-Step — not Claude), use Python for library maturity. Claude calls go
through Rust as CLI subprocesses.

## OTEL Observability Principle

Every backend fix that touches a subsystem MUST add OTEL watcher events so the GM panel
can verify the fix is working. Claude is excellent at "winging it" — writing convincing
narration with zero mechanical backing. The only way to catch this is OTEL logging on
every subsystem decision:

- **Intent classification** — what was the action classified as, and why?
- **Agent routing** — which agent handled the action (narrator vs creature_smith vs ensemble)?
- **State patches** — what changed in game state (HP, location, inventory)?
- **Inventory mutations** — items added/removed, with source (narration extraction, trade, etc.)
- **NPC registry** — NPCs detected, names assigned, collisions prevented
- **Trope engine** — tick results, keyword matches, activations
- **TTS segments** — what text was sent to voice synthesis

The GM panel is the lie detector. If a subsystem isn't emitting OTEL spans, you can't
tell whether it's engaged or whether Claude is just improvising.

**Not needed for:** Cosmetic UI changes (labels, spacing, colors).

## Spoiler Protection

Same rules as sq-2. See sq-2/CLAUDE.md for the full policy.
- **Fully spoilable:** `mutant_wasteland/flickering_reach` only
- **Fully unspoiled:** Everything else
