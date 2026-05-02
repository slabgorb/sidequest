# CLAUDE.md — SideQuest

This is the orchestrator repo for the SideQuest RPG Runner/Editor. It coordinates four subrepos:
- **sidequest-server** — Python/FastAPI game engine and WebSocket API (port 8765)
- **sidequest-ui** — React/TypeScript game client (Vite, port 5173)
- **sidequest-daemon** — Python media services (Flux/Z-Image generation, audio)
- **sidequest-content** — Genre packs (YAML configs, audio, images, world data)

## Who This Is For

SideQuest is built for a specific, real-world gaming group — not abstract personas. Design decisions should be weighed against these actual humans.

### Primary audience: Keith's playgroup

This is the group the game is *actually for*. Features must serve this group. If a decision trades playgroup quality for household reach, the playgroup wins.

- **Keith** — The builder, and the *forever-GM who finally wants to play*. Tarn-from-Dwarf-Fortress model: ~60% for himself, 40% for others. Senior architect, 40 years of tabletop, almost all of it behind the screen. Hits every axis — narrative *and* mechanical, high reading tolerance, fully bought in. **This is the single most load-bearing fact about the project:** SideQuest exists because Keith has been running games for four decades and wants the experience of being a player without losing the depth, agency, and surprise that a good human DM provides. Every design decision should ask "does this deliver a real player experience to someone who knows exactly what a good DM does?" The narrator must be *good enough to fool a career GM* — not just entertaining, but genuinely responsive, genre-true, and capable of surprising him. If the system can satisfy Keith-as-player, it can satisfy anyone.
- **James** (27, Keith's son) — Long-time playgroup member. Strong reader, narrative-first roleplayer. Played "Rux" in the Sunday caverns_and_claudes session — that save file is reference data for how he engages.
- **Alex** (playgroup) — Slower reader and typist; sometimes freezes when asked to roleplay under time pressure. Loves the game when paced inclusively. **Design implication:** sealed-letter turns, no fast-typist monopolies, generous response windows.
- **Sebastien** (Keith's nephew, ~James's age) — Plays on and off. The only **mechanics-first** player in the group — wants to know the rules, the numbers, how the system works. **Design implication:** the GM panel, OTEL visibility, and rule transparency aren't debug tools, they're a *feature* for Sebastien.

### Aspirational audience: the household

Nice-to-have, not load-bearing. If they never play, SideQuest is still a success. Don't bend primary-audience features to chase these users.

- **Sonia** (Keith's partner, lives with Keith) — The `victoria` genre pack is a love letter to her, not a feature gate. Has a nerd-force-field from years of living with nerds. Keith will live if she never plays.
- **Antonio & Pedro** (Sonia's sons, late 20s, share the household with Keith and Sonia as adults — Keith is not a parental figure to them) — Low reading tolerance, Pedro especially. Antonio is AI-skeptical and has his own playgroup; one of them is an artist. If visual/voice features happen to land for them, great — but don't compromise playgroup pacing or narrative depth to court them.

### Player-style axes

- *Narrative vs mechanical:* James/Alex narrative-first; Sebastien mechanical-first; Keith both.
- *Reading tolerance:* Keith/James high; Sebastien/Alex medium; household low.
- *RPG buy-in:* Keith/James/Sebastien/Alex committed; household ranges from skeptical to resistant.

### Using this rubric

When evaluating a feature, ask *which of these people it serves and which it loses.* Default to the playgroup. "Would Alex feel rushed by this?" and "Does Sebastien have enough mechanical visibility here?" are sharper design questions than "is this good UX?" Don't let aspirational users drag primary-audience decisions.

## Repository Structure

```
orc-quest/                    # This repo (orchestrator, also cloned as oq-1 / oq-2)
├── sprint/                   # Sprint tracking
├── docs/                     # Architecture docs and ADRs
│   ├── api-contract.md       # WebSocket + REST contract
│   ├── architecture.md       # System design and layer diagram
│   └── adr/                  # Architecture Decision Records
├── scripts/                  # Cross-repo scripts (playtest, music gen, etc.)
├── scenarios/                # Test/playtest scenarios
└── justfile                  # Cross-repo task runner

sidequest-content/            # Genre packs — single source of truth (subrepo)
├── genre_packs/
│   ├── caverns_and_claudes/
│   ├── elemental_harmony/
│   ├── heavy_metal/
│   ├── mutant_wasteland/
│   ├── space_opera/
│   ├── spaghetti_western/
│   └── <genre>/worlds/<world>/
└── CLAUDE.md

sidequest-server/             # Python FastAPI backend (subrepo, uv-managed)
├── sidequest/
│   ├── agents/               # Claude CLI subprocess orchestration (narrator; LocalDM preprocessor dormant per 2026-04-28 spec)
│   ├── cli/                  # Standalone CLIs (encountergen, loadoutgen, namegen, promptpreview, validate)
│   ├── daemon_client/        # Client for Python media daemon
│   ├── game/                 # State, characters, encounters, tropes, turns, persistence
│   ├── genre/                # YAML genre pack loader
│   ├── protocol/             # GameMessage, typed payloads (pydantic)
│   ├── server/               # FastAPI app, WebSocket, dispatch, sessions
│   └── telemetry/            # OTEL span definitions and watcher hooks
├── tests/
└── pyproject.toml

sidequest-ui/                 # React frontend (subrepo)
├── src/
│   ├── __tests__/
│   ├── audio/                # Music + SFX playback (no TTS)
│   ├── components/
│   ├── dice/                 # 3D dice overlay (Three.js + Rapier)
│   ├── hooks/
│   ├── lib/
│   ├── providers/
│   ├── screens/
│   ├── styles/
│   └── types/
└── package.json

sidequest-daemon/             # Python media services (subrepo)
├── sidequest_daemon/         # Package root
│   ├── audio/                # Music library, SFX mixer, scene interpreter
│   ├── genre/
│   ├── media/                # Flux / Z-Image generation pipeline
│   ├── ml/
│   └── renderer/
├── tests/
└── pyproject.toml
```

## Architecture

- **Server communicates via WebSocket** for real-time game events (narration, state updates)
- **Small REST surface** for save/load, character listing, genre pack metadata
- **Claude CLI (`claude -p`)** for all LLM calls — subprocess from Python, not SDK
- **Genre packs** live in `sidequest-content/genre_packs/` (single source of truth), loaded by the server from `SIDEQUEST_GENRE_PACKS`
- **Media daemon** is a Python sidecar for image/audio generation (Flux / Z-Image / ACE-Step)
- **Save files** live at `~/.sidequest/saves/` (SQLite `.db` files, one per genre/world session) — not in the repo. See `.pennyfarthing/guides/save-management.md` for cleanup, inspection, and migration procedures

### Port history

The backend was briefly a Rust workspace (`sidequest-api`, ~2026-03-30 to 2026-04-19). **ADR-082** ported it back to Python as `sidequest-server`; **ADR-085** governed tracker hygiene through cutover. The Rust tree no longer exists on disk locally, but is preserved as a read-only reference at **https://github.com/slabgorb/sidequest-api** — use it when an ADR references a Rust-specific layout and you need to trace the original implementation. Older ADRs that reference Rust-specific layouts (crates, `lib.rs`, cargo decomposition) are preserved as historical design records — see `docs/adr/README.md` for the port-era context header and per-ADR post-port mapping notes.

## Commands

All commands run from the orchestrator root. Services tee logs to `/tmp/sidequest-{server,client,daemon}.log`.

```bash
# Boot everything (daemon warmup → server → client, tails merged logs)
just up
just down                 # Stop all background services
just logs [service]       # Tail one or all service logs

# Individual services (foreground, Ctrl-C to stop)
just server               # FastAPI/uvicorn on :8765 (--reload)
just client               # Vite dev server on :5173
just daemon               # Media daemon with warmup

# Server (Python / uv)
just server-test          # uv run pytest -v
just server-lint          # uv run ruff check .
just server-fmt           # uv run ruff format .
just server-check         # lint + test

# Client (React)
just client-test          # npx vitest run
just client-build
just client-lint

# Daemon
just daemon-test
just daemon-lint          # ruff check
just daemon-status        # renderer status
just daemon-stop          # shutdown renderer

# Aggregate gate
just check-all            # server-check + client-lint + client-test + daemon-lint

# Playtest / OTEL
just playtest [flags]     # Headless playtest driver against running server
just playtest-scenario <name>   # Runs scenarios/<name>.yaml
just otel                 # Opens GM dashboard (sidequest-server /dashboard)

# Utilities
just status               # git status across all subrepos
just setup                # First-time: uv sync + npm install everywhere
just tmux                 # tmuxinator 4-pane dev session
```
## Development Principles


<critical>

### No Silent Fallbacks
If something isn't where it should be, fail loudly. Never silently try an alternative
path, config, or default. Silent fallbacks mask configuration problems and lead to
hours of debugging "why isn't this quite right."

</critical>



<critical>

### No Stubbing
Don't create stub implementations, placeholder modules, or skeleton code. If a feature
isn't being implemented now, don't leave empty shells for it. Dead code is worse than
no code.
</critical>

<critical>

### Don't Reinvent — Wire Up What Exists
Before building anything new, check if the infrastructure already exists in the codebase.
Many systems are fully implemented but not wired into the server or UI. The fix is
integration, not reimplementation.
</critical>

<critical>

### Verify Wiring, Not Just Existence
When checking that something works, verify it's actually connected end-to-end. Tests
passing and files existing means nothing if the component isn't imported, the hook isn't
called, or the endpoint isn't hit in production code. Check that new code has non-test
consumers.
</critical>

<critical>

### Every Test Suite Needs a Wiring Test
Unit tests prove a component works in isolation. That's not enough. Every set of tests
must include at least one integration test that verifies the component is wired into the
system — imported, called, and reachable from production code paths.
</critical>

<important>
## OTEL Observability Principle

Every backend fix that touches a subsystem MUST add OTEL watcher events so the GM panel
can verify the fix is working. Claude is excellent at "winging it" — writing convincing
narration with zero mechanical backing. The only way to catch this is OTEL logging on
every subsystem decision.

The GM panel is the lie detector. If a subsystem isn't emitting OTEL spans, you can't
tell whether it's engaged or whether Claude is just improvising.
</important>

## ADR Index

Architecture Decision Records live at `docs/adr/` — see `docs/adr/README.md` for the
authoritative index with summaries, status rationale, and the port-era reading
guide. This section is a compact category-keyed list for activation-time orientation.
Rust code samples in pre-ADR-082 ADRs are historical; translation table in
`docs/adr/README.md`.

<!-- ADR-INDEX:GENERATED:BEGIN -->

> Generated block. Edit frontmatter on individual ADRs + rerun `scripts/regenerate_adr_indexes.py`. Preamble above and `Conventions:` trailer below the markers are preserved.

**Load-bearing reads — start here:**
- **ADR-082** Port `sidequest-api` from Rust back to Python — accepted
- **ADR-085** Tracker hygiene during the Rust→Python port — handling port-drift — accepted
- **ADR-067** Unified Narrator Agent — Collapse Multi-Agent into Single Persistent Session — accepted
- **ADR-059** Monster Manual — Server-Side Pre-Generation via Game-State Injection — accepted
- **ADR-038** WebSocket Transport Architecture — accepted
- **ADR-035** Unix Socket IPC for Python Sidecar — accepted
- **ADR-014** Diamonds and Coal — accepted
- **ADR-088** ADR Frontmatter Schema and Auto-Generated Indexes — accepted

**Core Architecture (001, 002, 003, 004, 005, 006, 007)**
- 001 Claude CLI Only · 002 SOUL Principles · 003 Genre Pack Architecture · 004 Lazy Genre Binding · 005 Background-First Pipeline · 006 Graceful Degradation · 007 Unified Character Model

**Prompt Engineering (008, 009)**
- 008 Three-Tier Rule Taxonomy · 009 Attention-Aware Prompt Zones

**Agent System (011, 012, 066, 067)**
- 011 World State JSON Patches · 012 Agent Session Management · 066 Persistent Opus Narrator Sessions · **067 Unified Narrator Agent — Collapse Multi-Agent into Single Persistent Session**

**Game Systems (014, 015, 016, 018, 020, 021, 022, 023, 024, 025, 080)**
- **014 Diamonds and Coal** · 015 Character Builder State Machine · 016 Three-Mode Character Creation · 018 Trope Engine *(partial)* · 020 NPC Disposition System *(partial)* · 021 Progression System · 022 WorldBuilder Maturity · 023 Session Persistence · 024 Dual-Track Tension Model · 025 Pacing Detection · 080 Unified Narrative Weight Trait

**Frontend / Protocol (026, 027, 079)**
- 026 Client-Side State Mirror · 027 Reactive State Messaging · 079 Genre Theme System Unification

**Multiplayer (028, 036, 037)**
- 028 Perception Rewriter · 036 Multiplayer Turn Coordination · 037 Shared-World / Per-Player State Split

**Transport / Infrastructure (035, 038, 046, 047)**
- **035 Unix Socket IPC for Python Sidecar** · **038 WebSocket Transport Architecture** · 046 GPU Memory Budget Coordinator · 047 Prompt Injection Sanitization Layer

**Narrator / Text (040, 049, 052, 057)**
- 040 Narrative Character Sheet (No Raw Stats) · 049 Narrator Verbosity and Vocabulary (Two-Axis Text Tuning) · 052 Narrative Axis System (/tone Command) · 057 Narrator Crunch Separation — LLM Narrates, Scripts Crunch *(partial)*

**NPC / Character Systems (041, 042, 053, 091)**
- 041 Genie Wish / Consequence Engine *(drift)* · 042 OCEAN Personality Live Evolution *(drift)* · 053 Scenario System (Clue Graph, Belief State, Gossip Propagation) *(partial)* · 091 Culture-Corpus + Markov Naming

**Media / Audio / Rendering (045, 048, 050, 070)**
- 045 Client Audio Engine *(partial)* · 048 Lore RAG Store with Cross-Process Embedding · 050 Image Pacing Throttle · 070 MLX Image Renderer — Replace PyTorch/diffusers with Apple MLX

**Turn Management (051)**
- 051 Two-Tier Turn Counter (Interaction vs. Round)

**Code Generation / Tooling (059, 069)**
- **059 Monster Manual — Server-Side Pre-Generation via Game-State Injection** *(drift)* · 069 Scenario Fixtures — Pre-configured World States for Testing *(partial)*

**Observability (090)**
- 090 OTEL Dashboard Restoration after Python Port

**Codebase Decomposition (060, 061, 062, 063, 064, 068, 088)**
- 060 Genre Models Decomposition — Split models.rs by Domain · 061 Lore Module Decomposition — Split lore.rs by Responsibility · 062 Server lib.rs Extraction — Route Groups, State, and Watcher Events · 063 Dispatch Handler Splitting — By Pipeline Stage · 064 Game Crate Domain Modules — Organize 69 Flat Files · 068 Magic Literal Extraction — Domain-Scoped Constants · **088 ADR Frontmatter Schema and Auto-Generated Indexes**

**Narrator Architecture (073)**
- 073 Local Fine-Tuned Model Architecture

**Genre Mechanics (031, 033)**
- 031 Game Watcher — Semantic Telemetry for AI Agent Observability · 033 Genre Mechanics Engine — Confrontations & Resource Pools *(partial)*

**Project Lifecycle / Meta (082, 085)**
- **082 Port `sidequest-api` from Rust back to Python** · **085 Tracker hygiene during the Rust→Python port — handling port-drift**

**Conventions:** Bold = load-bearing for current architecture. `drift`/`partial`/`deferred` in a line means the ADR is accepted but implementation is not fully live — see [DRIFT.md](docs/adr/DRIFT.md). Superseded/historical ADRs are filtered from this view — see [SUPERSEDED.md](docs/adr/SUPERSEDED.md).

<!-- ADR-INDEX:GENERATED:END -->
