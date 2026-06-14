# SideQuest — AI Dungeon Master

An AI narrator engine that runs tabletop-style RPGs in any genre, powered by an
Anthropic-SDK-backed Claude narrator (ADR-101 default; Haiku 4.5 classification /
Sonnet 4.6 narration / Opus 4.7 declared-important moments, routed per call)
invoked stateless per turn (ADR-098), with native
tool-use for structured mechanical patches (ADR-102) and native OTEL via the
tool registry (ADR-103). Players connect via browser, create characters
through genre-driven scenes, and explore worlds — including the runtime
procedural Jaquaysed megadungeon `beneath_sunden` (ADR-106) — with real-time
image generation (Z-Image MLX), streaming narration, adaptive music, and
pre-rendered tactical maps. Multiplayer uses submit-and-wait turn barriers,
perception rewriting at the tool layer (ADR-104), live teammate typing,
collaborative peer-action visibility (ADR-036), and a non-turn-consuming
out-of-band aside channel for OOC table-talk (ADR-107).

## Repository Ecosystem

```
┌──────────────────────────────────────────────────────────────┐
│  sidequest (this repo) — Orchestrator                        │
│  Sprint tracking, cross-repo justfile, architecture docs     │
└──────┬──────────────┬──────────────┬──────────────┬──────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌──────────────┐ ┌───────────┐ ┌──────────────┐ ┌────────────────┐
│sidequest-    │ │sidequest- │ │sidequest-    │ │sidequest-      │
│server (Py)   │ │  ui (TS)  │ │daemon (Py)   │ │content         │
│              │ │           │ │              │ │                │
│ FastAPI +    │ │ React 19  │ │ Z-Image      │ │ Genre pack     │
│ uvicorn      │ │ client    │ │ (MLX)        │ │ YAML + audio   │
│ WebSocket    │ │ Audio     │ │ renderer     │ │ params + LFS   │
│ Narrator     │ │ engine    │ │ ACE-Step     │ │ images         │
│ Anthropic SDK│ │ 3D dice   │ │ music tier   │ │ 11 live packs  │
│ (ADR-101)    │ │ overlay   │ │ + SFX mixer  │ │ (draft-gated)  │
└──────────────┘ └───────────┘ └──────────────┘ └────────────────┘
       ▲              │              ▲
       │  WebSocket   │   Unix sock  │
       └──────────────┴──────────────┘

   sidequest-composer (Py) — standalone, offline. Public-domain
   notation (MusicXML/MIDI) → tagged rights-free audio via MuseScore 4
   / FluidSynth. Not wired into the runtime; a build-time content tool.

   sidequest-understudy (Py) — naive simulated-player playtest client.
   Bots join a real session through the React UI and role-play a seat,
   one LLM call per turn. A test harness, not part of the runtime;
   interface confusion is a finding (the naivety invariant).
```

| Repo | Language | Purpose | GitHub |
|------|----------|---------|--------|
| **sidequest** | — | Orchestrator, docs, sprint tracking | slabgorb-org/sidequest |
| **sidequest-server** | Python | Game engine, FastAPI WebSocket API, narrator orchestration | slabgorb-org/sidequest-server |
| **sidequest-ui** | TypeScript | React 19 client, audio engine, 3D dice overlay | slabgorb-org/sidequest-ui |
| **sidequest-daemon** | Python | Media services (Z-Image image gen, ACE-Step music, SFX mixer) | slabgorb-org/sidequest-daemon |
| **sidequest-content** | YAML | Genre pack configs, audio, images, worlds | slabgorb-org/sidequest-content |
| **sidequest-composer** | Python | Standalone CLI: public-domain notation → tagged, rights-free audio (deterministic synthesis, not AI) | slabgorb-org/sidequest-composer |
| **sidequest-understudy** | Python | Naive simulated-player playtest client — bots join real sessions through the UI and role-play a seat | slabgorb-org/sidequest-understudy |

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
just check-all      # server-check + client lint/build/test + daemon lint/test + composer lint/test
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

Logs tee to `~/.sidequest/logs/sidequest-{server,client,daemon}.log` (moved out of `/tmp`
so reboots don't eat them; each launch rotates the prior file to `.log.YYYYMMDD-HHMMSS`,
30-day retention). Use `just logs` to tail all of them, or `just logs server` for one.

See [`docs/playtest-cookbook.md`](docs/playtest-cookbook.md) for how to test specific features
and [`scenarios/`](scenarios/) for headless playtest YAML driven by `just playtest-scenario`.

## Genre Packs

Eleven narrative packs are live and wired into the runtime, each with its own
rules, tropes, character creation, audio, visual style, faction agendas, OCEAN
personality archetypes, and conlang morphemes:

| Pack | Theme | Worlds |
|------|-------|--------|
| **caverns_and_claudes** | High fantasy dungeon crawl (meta-humor on D&D tropes) | `beneath_sunden` (runtime procedural megadungeon, ADR-106) |
| **elemental_harmony** | Martial arts / elemental magic (WWN ruleset) | `burning_peace`, `shattered_accord` |
| **heavy_metal** | Baroque fantasy of pacts, decay, and blood-priced magic | `evropi`, `long_foundry`, `barsoom` (WWN ruleset; portraits still rendering) |
| **mutant_wasteland** | Post-apocalyptic mutants (`flickering_reach` fully spoilable) | `flickering_reach`, `seaboard_of_saints` |
| **neon_dystopia** | Cyberpunk (CWN ruleset) | `franchise_nations` |
| **pulp_noir** | 1930s detective / pre-war pulp | `annees_folles` |
| **road_warrior** | Late-70s / early-80s vehicle subcultures sharing one port city | `the_circuit` |
| **space_opera** | Sci-fi space adventure (SWN ruleset) | `aureate_span`, `coyote_star`, `perseus_cloud` |
| **spaghetti_western** | Morally ambiguous anti-heroes — Leone/Corbucci/Kurosawa | `dust_and_lead`, `five_points` (1850s NYC), `the_real_mccoy` (1878 Pittsburgh) |
| **tea_and_murder** | Cosy Edwardian (1901-1914) BritBox murder mystery | `glenross` (Highland village), `blackthorn_moor` |
| **wry_whimsy** | Golden-age literary portal fairytale — survive by wit, not force | `oz`, `wonderland`, `gulliver` |

All eleven packs have a `pack.yaml` and load at runtime. Worlds default to live;
`draft: true` in a world's `world.yaml` hides it from selection until its asset
gate (portraits + POI landscapes rendered to R2) is met — there are currently no
draft worlds (all 22 are live). The old `genre_workshopping/` staging tree was
**retired 2026-06-03**; in-progress packs and worlds now live in `genre_packs/`
like any other and rely on `draft` status to stay hidden.

Genre packs are loaded via the `SIDEQUEST_GENRE_PACKS` env var. See
[`docs/genre-pack-status.md`](docs/genre-pack-status.md) for per-pack completeness.

## How It Works

1. **Player connects** via WebSocket from the React client
2. **Character creation** flows through genre-driven scenes (choices + freeform text);
   the C&C pack offers a visible-dice flow with arrange + story steps and four classic
   B/X classes (fighter / mage / cleric / thief)
3. **Each turn:** player action → narrator dispatch → state patch → narration broadcast
4. **Unified narrator** (per [ADR-067](docs/adr/067-unified-narrator-agent.md), invoked
   stateless per turn per [ADR-098](docs/adr/098-stateless-narrator-turns.md)) handles
   all intents through a single bounded **Anthropic SDK** call
   ([ADR-101](docs/adr/101-anthropic-sdk-as-narrator-backend.md), supersedes ADR-001 —
   prompt caching, native tool-use, model routing; `claude -p`/Ollama are opt-in
   non-default backends). Auxiliary subsystem agents
   (chassis_voice, distinctive_detail, npc_agency, reflect_absence) run topologically
   off the live turn critical path. Streaming narration is opt-in and **default-off**
   (`SIDEQUEST_NARRATOR_STREAMING=1` enables it, routing to the legacy `claude -p` path)
5. **Media pipeline:** narration triggers Z-Image MLX renders and mood-based audio
   cues in parallel — background-first, only text is critical path
   ([ADR-005](docs/adr/005-background-first-pipeline.md)). Renders and music both
   upload to R2; pre-rendered cellular caverns ship as PNG tactical maps (ADR-096).
   Music is generated on operator command via `scripts/generate_music.py` (ADR-095)
6. **Magic system** (Epic 47): three plugins live — `innate_v1`, `item_legacy_v1`, and
   `learned_v1` (Vancian memorization for C&C). Ledger bars track per-character magic
   state; Coyote Star v1 wires five named magic confrontations (the_standoff,
   the_salvage, the_bleeding_through, the_quiet_word, the_long_resident) that resolve
   through the Phase-5 `auto_fire_trigger` threshold evaluator plus the rig-coupled
   room-entry evaluator, against the confrontation list loaded at session init
7. **Pacing engine:** dual-track TensionTracker produces `drama_weight` (0.0–1.0) →
   controls narration length, delivery speed, beat escalation, and media render gating
8. **World systems:** faction agendas inject per-turn, trope engine drives narrative arcs,
   world materialization tracks campaign maturity, orbital chart drives space-scene
   navigation (ADR-094)
9. **NPC personality:** OCEAN Big Five profiles shape NPC dialogue and behavior, shifting
   over time from game events
10. **Knowledge:** KnownFacts accumulate from play with footnoted narrator callbacks,
    Knowledge Journal supports keyword filtering, lore fragments seed from genre packs,
    conlang names generated from culture corpora via Markov
    ([ADR-091](docs/adr/091-culture-corpus-markov-naming.md))
11. **Combat:** Ablative HP is the live personal survivability track on `CreatureCore`
    (ADR-114, reversing ADR-078's HP removal). The bound ruleset module selects combat
    resolution — three HP-based Without-Number rulesets (all attack-vs-AC, `hp_depletion`)
    are live: SWN for space_opera, WWN for elemental_harmony, CWN for neon_dystopia; B/X or
    3.5 SRD (both HP-based) are planned for caverns_and_claudes. Edge / Composure dials
    (ADR-078) are planned to return as the Fate SRD substrate — "for different engines,"
    not yet co-resident. (Vessel rig-composure survives separately.) 3D dice (Three.js +
    Rapier) render inline in the confrontation overlay
12. **Multiplayer:** submit-and-wait turn barriers with adaptive timeout, Cinematic
    mode as the live default (FREE_PLAY available; STRUCTURED dead code), collaborative
    peer-action visibility with live teammate typing via `ACTION_REVEAL`, perception
    rewriting (see ADR-036 for the visibility doctrine; sealed-visibility mode is
    reserved for PvP and not yet implemented)

## Server Module Layout

```
sidequest-server/sidequest/
├── protocol/         # GameMessage, typed payloads (pydantic)
├── server/           # FastAPI app, WebSocket, dispatch, sessions
├── handlers/         # Per-message-type dispatch handlers
├── agents/           # Anthropic SDK narrator (default) + claude -p/Ollama opt-in, auxiliaries
├── game/             # State, characters, encounters, tropes, turns, persistence
│                     #   game/ruleset/ — pluggable SRD modules (native + Without Number family)
├── dungeon/          # Runtime procedural Jaquaysed megadungeon (ADR-106)
├── mutation/         # AWN mutation system — acquire / use / stocks (ADR-102)
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
                      #   validate, weathergen, cookbook_ingest,
                      #   corpusmine, corpuslabel, corpusdiff
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
- [`JARGONFILE.md`](JARGONFILE.md) — Glossary of project jargon (Forge theory terms, engine nouns, narrator doctrine, subsystem names)

### Project Status
- [`docs/feature-inventory.md`](docs/feature-inventory.md) — Feature inventory: done, wired, planned
- [`docs/genre-pack-status.md`](docs/genre-pack-status.md) — Per-pack content completeness

## Sprint Tracking

Sprint plans live in `sprint/` as YAML files with per-story context documents.
See `sprint/current-sprint.yaml` for active work and `sprint/archive/` for completed stories.
# .github-private
