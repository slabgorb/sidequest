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
- **Alex** (playgroup) — Slower reader and typist; sometimes freezes when asked to roleplay under time pressure. Loves the game when paced inclusively. **Design implication:** submit-and-wait turn barrier (no narration until everyone submits — never rush a slow typist), no fast-typist monopolies, generous response windows. Peer action text *is* visible during the wait phase per ADR-036's 2026-05-03 amendment — collaborative visibility helps the table coordinate. Hidden-submission ("sealed visibility") mode is reserved for PvP scenarios and not currently implemented; the playgroup doesn't slip notes to the DM. See ADR-036 doctrine clarification (2026-05-09).
- **Sebastien** (Keith's nephew, ~James's age) — Plays on and off. A **mechanics-first** player (with Jade, one of two in the group) — wants to know the rules, the numbers, how the system works. **Design implication:** in **player-facing** surfaces, expose the math behind mechanical resolution (dice rolls, beat selection, ability costs, advancement deltas) so he doesn't have to guess what just happened. This is a player-UI consideration — *not* an excuse to invoke his name for OTEL spans, the GM panel, watcher telemetry, or any other dev-side observability. Those exist so the dev (Keith) can verify the engine works; Sebastien doesn't see them and isn't served by them. If you're tempted to write "Sebastien's lie-detector" about a backend OTEL emit or a GM-panel chart, you've made the wrong association — that's a Keith/dev tool, not a Sebastien feature.
- **Jade** (introduced to the group by Sebastien; not previously known to Keith) — A long-time DM in her own right — like Keith, a **forever-GM who also wants to play along** — and, as of **2026-05-29**, **one of the people who writes content.** She isn't *the* content author — Keith authors too, and others may — but she's the first *non-Keith* author to come aboard, which makes her a concrete instance of the project's real goal: **the authoring surfaces must handle homebrew.** She's playing / extending `genre_packs/space_opera/worlds/perseus_cloud`, onboarded onto a paste-new-stuff-in / **pull-request** update path (better tools and wizards to follow). The load-bearing requirement she stands for is that *anyone* — Jade, Keith, a future table member — can add worlds, packs, rules, and lore **as content** (pack/world YAML, world overrides, the "Yes, And" collaborative-worldbuilding path) **without touching engine code**. If authoring what a table wants requires a server change, that's a failure of the content surface. Her instincts run **mechanics-first**: with Sebastien she ran the 5-hour, 140+ turn `coyote_star` session *while the confrontation engine was broken* and carried it on narrative, NPC, and relationship strength alone — and the two of them specifically miss the crunch that wasn't firing. **Two design implications.** (1) As a *player*, she wants mechanical resolution legible in **player-facing** surfaces — a player-UI consideration, not a license for her name on OTEL/GM-panel/dev observability. (2) As an *author*, the crunch a table wants must be **expressible in homebrew content**, not buried in engine code. The 2026-05-25 SWN-crunch / ablative-HP reintroduction (`docs/superpowers/specs/2026-05-25-swn-crunch-ablative-hp-design.md`) is a direct response to Sebastien + Jade.

### Aspirational audience: the household

Nice-to-have, not load-bearing. If they never play, SideQuest is still a success. Don't bend primary-audience features to chase these users.

- **Sonia** (Keith's partner, lives with Keith) — The `tea_and_murder` genre pack is a love letter to her, not a feature gate. Has a nerd-force-field from years of living with nerds. Keith will live if she never plays.
- **Antonio & Pedro** (Sonia's sons, late 20s, share the household with Keith and Sonia as adults — Keith is not a parental figure to them) — Low reading tolerance, Pedro especially. Antonio is AI-skeptical and has his own playgroup; one of them is an artist. If visual/voice features happen to land for them, great — but don't compromise playgroup pacing or narrative depth to court them.

### Player-style axes

- *Narrative vs mechanical:* James/Alex narrative-first; Sebastien/Jade mechanical-first; Keith both. (Sebastien/Jade also love narrative — they carried a 140-turn game on it — but feel the absence of crunch.)
- *Reading tolerance:* Keith/James/Jade high; Sebastien/Alex medium; household low.
- *RPG buy-in:* Keith/James/Sebastien/Jade/Alex committed; household ranges from skeptical to resistant.

### Using this rubric

When evaluating a feature, ask *which of these people it serves and which it loses.* Default to the playgroup. "Would Alex feel rushed by this?" and "Can Sebastien see the math in the player UI here?" are sharper design questions than "is this good UX?" Don't let aspirational users drag primary-audience decisions. (Note the "in the player UI" framing — questions about backend observability, OTEL coverage, or GM-panel completeness are Keith/dev concerns, not Sebastien concerns.)

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
├── JARGONFILE.md             # Glossary of project jargon (Forge terms, engine nouns, doctrine)
└── justfile                  # Cross-repo task runner

sidequest-content/            # Genre packs — single source of truth (subrepo)
├── genre_packs/              # Live, wired packs (10: caverns_and_claudes, elemental_harmony,
│   │                         #   heavy_metal, mutant_wasteland, neon_dystopia, pulp_noir,
│   │                         #   road_warrior, space_opera, spaghetti_western, tea_and_murder).
│   │                         # neon_dystopia (franchise_nations) + pulp_noir (annees_folles)
│   │                         #   asset gates now MET (portraits + POI landscapes rendered to
│   │                         #   R2). heavy_metal: evropi complete, long_foundry portraits
│   │                         #   pending. space_opera adds aureate_span (baroque corona
│   │                         #   megastation, live) + perseus_cloud. spaghetti_western adds
│   │                         #   five_points. tea_and_murder adds blackthorn_moor (draft,
│   │                         #   assets pending). Remaining asset gaps: long_foundry portraits,
│   │                         #   coyote_star POIs, blackthorn_moor (all). See pack README.
│   └── <genre>/worlds/<world>/   # World-specific overrides
├── genre_workshopping/       # Pre-wired packs in design (caverns_sunden — deprecated;
│                             #   low_fantasy).
│                             #   Subdirs named like a live pack hold in-progress
│                             #   alternate worlds for that pack.
├── corpus/                   # Conlang word lists per culture (ADR-091)
├── tools/                    # Pack authoring tooling
├── PROMPTING_Z_IMAGE.md      # Z-Image prompting guide
├── README.md
└── CLAUDE.md

sidequest-server/             # Python FastAPI backend (subrepo, uv-managed)
├── sidequest/
│   ├── agents/               # Narrator backends — Anthropic SDK (default) + claude -p/Ollama opt-in; LocalDM preprocessor dormant per 2026-04-28 spec
│   ├── audio/                # Server-side music + SFX coordination
│   ├── cli/                  # Standalone CLIs (encountergen, loadoutgen, namegen, validate, corpus*)
│   ├── corpus/               # Conlang corpus + Markov naming (ADR-091)
│   ├── daemon_client/        # Client for Python media daemon
│   ├── game/                 # State, characters, encounters, tropes, turns, persistence (~70 modules)
│   ├── genre/                # YAML genre pack loader
│   ├── handlers/             # Per-message-type dispatch handlers
│   ├── interior/             # Room / interior state
│   ├── magic/                # Magic system mechanics
│   ├── media/                # Image generation orchestration (daemon client wrapper)
│   ├── orbital/              # Orbital / space-scene mechanics
│   ├── protocol/             # GameMessage, typed payloads (pydantic v2)
│   ├── renderer/             # Render scheduling + throttle (ADR-050)
│   ├── server/               # FastAPI app, WebSocket, dispatch, sessions, watcher
│   └── telemetry/            # OTEL span definitions and watcher hooks
├── tests/
└── pyproject.toml

sidequest-ui/                 # React frontend (subrepo)
├── src/
│   ├── __tests__/
│   ├── assets/               # Static assets (icons, fonts)
│   ├── audio/                # Music + SFX playback (no TTS, post-2026-04)
│   ├── components/           # GameBoard, NarrationCards, PartyPanel, Dashboard/, etc.
│   ├── dice/                 # 3D dice overlay (Three.js + Rapier, ADR-075)
│   ├── hooks/                # useWebSocket, useGameSocket, useStateMirror, useGenreTheme, etc.
│   ├── lib/
│   ├── providers/            # GameState, ImageBus, Theme
│   ├── screens/              # ConnectScreen, CharacterCreation, NarrativeView
│   ├── styles/
│   └── types/                # WebSocket payload TypeScript definitions
└── package.json

sidequest-daemon/             # Python media services (subrepo)
├── sidequest_daemon/         # Package root
│   ├── audio/                # pygame-ce mixer (music + SFX, no TTS)
│   ├── genre/                # Genre pack model subset (VisualStyle, AudioConfig)
│   ├── media/
│   │   ├── workers/          # zimage_mlx_worker.py — sole runtime image worker (ADR-070)
│   │   ├── music_pipeline.py # ACE-Step → ffmpeg → R2 (ADR-095, operator-triggered)
│   │   ├── prompt_composer.py, subject_extractor.py, recipes.py, ...
│   │   └── daemon.py         # Unix socket server + CLI entry
│   ├── ml/                   # GPU memory management (ADR-046)
│   ├── renderer/             # Data models (StageCue, RenderTier, RenderResult)
│   └── scene_interpreter.py
├── tests/
└── pyproject.toml
```

## Architecture

- **Server communicates via WebSocket** for real-time game events (narration, state updates)
- **Small REST surface** for save/load, character listing, genre pack metadata
- **Anthropic Python SDK** is the default narrator LLM backend per **ADR-101** (supersedes ADR-001): prompt caching, native tool-use (replaces the ADR-039 JSON sidecar via ADR-102), per-call model routing (Haiku/Sonnet/Opus). Backend is selected by `SIDEQUEST_LLM_BACKEND` (default `anthropic_sdk`) — see `sidequest-server/sidequest/agents/llm_factory.py`. The `claude -p` CLI subprocess and Ollama remain opt-in non-default backends, and `claude -p` still serves some non-narrator jobs (e.g. dungeon "curate")
- **Genre packs** live in `sidequest-content/genre_packs/` (single source of truth), loaded by the server from `SIDEQUEST_GENRE_PACKS`. A pack can bind a pluggable ruleset module via `ruleset:` in its `rules.yaml` (`native` is the default; `swn` = Stars Without Number). `space_opera` binds `swn`
- **Media daemon** is a Python sidecar for image generation (Flux / Z-Image) and music generation (ACE-Step). Music is generated on operator command via `python scripts/generate_music.py --genre <pack>` — per-track JSON params files in `sidequest-content/genre_packs/<pack>/audio/music/*_input_params.json` are the canonical spec; the daemon uploads OGG to R2 at `genre_packs/<pack>/audio/music/<track>.ogg`. See ADR-095
- **Save files** live in a single **PostgreSQL** database (one `sessions` table: integer `session_id` PK + `session_slug` TEXT UNIQUE), per **ADR-115** (complete). The per-file SQLite model is **retired** — the SQLite write layer (`SqliteStore`/`SqliteSaveRepository`) was deleted, not dual-pathed. Config requires `SIDEQUEST_DATABASE_URL`: there is **no silent default** — unset raises `MissingDatabaseUrlError`, and the app fails loud at startup if Postgres is unreachable (pool wait timeout 10s), honoring "No Silent Fallbacks". Connectivity is psycopg3 + `psycopg_pool.ConnectionPool`; concurrency uses per-session row locks (`SELECT ... FOR UPDATE`); Alembic owns all DDL (raw SQL via `op.execute`, no ORM). Old `~/.sidequest/saves/*.db` files are never written anymore — a read-only importer (`python -m sidequest.game.importer`) imports one legacy `.db` at a time. See `.pennyfarthing/guides/save-management.md` for cleanup, inspection, and migration procedures

### Port history

The backend was briefly a Rust workspace (`sidequest-api`, ~2026-03-30 to 2026-04-19). **ADR-082** ported it back to Python as `sidequest-server`; **ADR-085** governed tracker hygiene through cutover. The Rust tree no longer exists on disk locally, but is preserved as a read-only reference at **https://github.com/slabgorb/sidequest-api** — use it when an ADR references a Rust-specific layout and you need to trace the original implementation. Older ADRs that reference Rust-specific layouts (crates, `lib.rs`, cargo decomposition) are preserved as historical design records — see `docs/adr/README.md` for the port-era context header and per-ADR post-port mapping notes.

## Commands

All commands run from the orchestrator root. Services tee logs to `~/.sidequest/logs/sidequest-{server,client,daemon}.log` (moved out of `/tmp` so reboots don't eat them; rotated per launch with timestamped `.log.YYYYMMDD-HHMMSS` backups, 30-day retention). Re-tail with `just logs [service]` or `tail -F ~/.sidequest/logs/sidequest-server.log`. (Some older code comments still reference the retired `/tmp/sidequest-server.log` path.)

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
- **ADR-067** Unified Narrator Agent — Collapse Multi-Agent into Single Narrator — accepted
- **ADR-059** Monster Manual — Server-Side Pre-Generation via Game-State Injection — accepted
- **ADR-038** WebSocket Transport Architecture — accepted
- **ADR-035** Unix Socket IPC for Python Sidecar — accepted
- **ADR-014** Diamonds and Coal — accepted
- **ADR-088** ADR Frontmatter Schema and Auto-Generated Indexes — accepted

**Core Architecture (002, 003, 004, 005, 006, 007, 101, 115, 120, 121, 135)**
- 002 SOUL Principles · 003 Genre Pack Architecture · 004 Lazy Genre Binding · 005 Background-First Pipeline · 006 Graceful Degradation · 007 Unified Character Model · 101 Anthropic SDK as Narrator Backend *(partial)* · 115 Persistence Substrate Migration — SQLite-Per-Session to PostgreSQL · 120 Genre/World Flavor Boundary — Mandatory-File Loader Contract, Mechanics-in-Genre, Flavor-in-World · 121 Layered Content Resolution — Global→Genre→World→Culture Merge with Per-Field Strategies and Provenance · 135 Reference Pages Are a Public Table Tool — Single Fixed Projection, No GM Audience *(deferred)*

**Prompt Engineering (008, 009)**
- 008 Three-Tier Rule Taxonomy · 009 Attention-Aware Prompt Zones

**Agent System (011, 012, 013, 067, 098, 100, 102, 110, 111, 112, 113, 118, 123, 134)**
- 011 World State JSON Patches · 012 Agent Session Management · 013 Lazy JSON Extraction *(drift)* · **067 Unified Narrator Agent — Collapse Multi-Agent into Single Narrator** · 098 Stateless Narrator Turns — Drop --resume, Bounded Per-Turn Prompts · 100 Journal Pipeline Coherence — Footnotes, KnownFacts, JOURNAL_RESPONSE, and the Scenario Clue Hook *(partial)* · 102 Tool-Use Protocol for Structured Output *(partial)* · 110 Game-State Snapshot Slimming — Compact Encoding + Allowlist Pruning, Diff-with-Anchor Deferred *(partial)* · 111 Recency-Zone Narrator Guardrails Migrate to Tool Descriptions and Primacy-Cached Output Prose *(deferred)* · 112 Genre Prose Cache Promotion — Four Always-Fire Session-Static Sections Move to Stable, Conditional Sections Defer *(partial)* · 113 Intent Router — Mechanical-Engagement Spine *(partial)* · 118 Universal Retrieval Layer — Index + Per-Turn Floor-and-Fill Retrieval for NPCs, Locations, and Factions *(deferred)* · 123 Mechanical-Engagement Pipeline — Confidence-Gated Topological Dispatch Bank, Precondition/Unregistered Gates, and the LethalityArbiter · 134 Per-Session API Cost Runaway Detector and Hard-Kill Ceiling — Rolling-Baseline Triggers and Terminal Refusal

**Game Systems (014, 015, 016, 018, 020, 021, 022, 023, 024, 025, 074, 077, 080, 081, 096, 097, 106, 109, 114, 116, 117, 125, 126, 128, 129, 130)**
- **014 Diamonds and Coal** · 015 Character Builder State Machine · 016 Three-Mode Character Creation · 018 Trope Engine *(drift)* · 020 NPC Disposition System · 021 Progression System · 022 WorldBuilder Maturity · 023 Session Persistence · 024 Dual-Track Tension Model · 025 Pacing Detection · 074 Dice Resolution Protocol — Player-Facing Rolls via WebSocket · 077 Dogfight Subsystem via StructuredEncounter Extension · 080 Unified Narrative Weight Trait · 081 Advancement Effect Variant Expansion (v1) *(deferred)* · 096 Cavern Renderer Revival — Pre-Rendered Cellular Caverns for Tactical Maps *(partial)* · 097 Class Mechanical Surface — One Signature Ability Per Non-Magical Class · 106 Runtime Procedural Jaquaysed Megadungeon — Contiguous Edge-Expansion, maze-maker Family Port + Complication Ledger *(partial)* · 109 Persistent Location Descriptions + Mechanical Manifest *(partial)* · 114 Ablative HP Substrate — HP Reclaims the Lethality Track Beneath the Dials *(partial)* · 116 A Confrontation Requires an Other — Participant Membership Invariant, Single Opponent-Seater, End-on-No-Other *(partial)* · 117 Pluggable Ruleset Module System — Per-Genre Resolution Behind a RulesetModule Seam *(partial)* · 125 Chassis/Rig as a First-Class Entity — Bidirectional Bond Ledger, Seven-Tier Threshold Ladder, and Interior Render · 126 Pluggable Magic System — MagicPlugin Protocol, Import-Time Registry, and Validator Severity Model · 128 Trope Temporal Governor, Seed-Trope Deck, and NPC Development Ladder — Pile-Up Prevention and Resume-Safe Randomness · 129 N-Seat Table Engine — Generalized Sealed-Commit Loop for Poker/Auction with Cheat/Accuse Mechanics · 130 Orbital Story-Time Clock and Course Model — Beat-Driven Time Advance and Approximate Hohmann Transit

**Frontend / Protocol (026, 027, 075, 079, 094, 107, 133)**
- 026 Client-Side State Mirror · 027 Reactive State Messaging · 075 3D Dice Rendering — Three.js + Rapier Physics Overlay *(partial)* · 079 Genre Theme System Unification · 094 Orrery Label Placement — Three-Strategy Taxonomy · 107 Out-of-Band Aside Channel — Non-Turn-Consuming Player→GM Table-Talk · 133 Client State Reconciliation v2 — Full-Replay Mirror, Streaming-Narration Accumulator, and ImageBus Scrapbook Merge

**Multiplayer (036, 037, 104, 105, 108, 119, 122)**
- 036 Multiplayer Turn Coordination · 037 Shared-World / Per-Player State Split · 104 Perception Filtering at the Tool Layer *(partial)* · 105 Broadcast-Layer Perception Firewall — Completing ADR-104 in the MP Fan-Out *(partial)* · 108 MP Item Attribution — Per-Recipient Tagging in the Narration Tool Contract · 119 Authenticated Player Identity — Player-vs-Character Identity Split via Cloudflare Access *(partial)* · 122 SessionRoom Lifecycle — RoomRegistry Never-Evict Policy, LobbyState FSM, Multi-Socket Presence Ref-Counting

**Transport / Infrastructure (035, 038, 046, 047, 131)**
- **035 Unix Socket IPC for Python Sidecar** · **038 WebSocket Transport Architecture** · 046 GPU Memory Budget Coordinator · 047 Prompt Injection Sanitization Layer · 131 Daemon↔Server Out-of-Band Contracts — Liveness Heartbeat, OTEL HTTP Bridge, Output-Dir Handshake, R2 Artifact Layout

**Narrator / Text (040, 049, 052)**
- 040 Narrative Character Sheet (No Raw Stats) · 049 Narrator Verbosity and Vocabulary (Two-Axis Text Tuning) · 052 Narrative Axis System (/tone Command)

**NPC / Character Systems (041, 042, 053, 091)**
- 041 Genie Wish / Consequence Engine *(drift)* · 042 OCEAN Personality Live Evolution *(drift)* · 053 Scenario System (Clue Graph, Belief State, Gossip Propagation) *(partial)* · 091 Culture-Corpus + Markov Naming

**Media / Audio / Rendering (045, 048, 050, 070, 086, 095, 127)**
- 045 Client Audio Engine · 048 Lore RAG Store with Cross-Process Embedding · 050 Image Pacing Throttle · 070 MLX Image Renderer — Replace PyTorch/diffusers with Apple MLX · 086 Image-Composition Taxonomy — Portraits, POIs, Illustrations · 095 Daemon Music Tier via ACE-Step · 127 Image Prompt-Composition Pipeline — Catalog Recipes, Token-Budget Eviction Ladder, and SceneInterpreter Rule Cascade

**Turn Management (051)**
- 051 Two-Tier Turn Counter (Interaction vs. Round)

**Room Graph / Dungeon Crawl (055)**
- 055 Room Graph Navigation *(partial)*

**Code Generation / Tooling (059, 092)**
- **059 Monster Manual — Server-Side Pre-Generation via Game-State Injection** · 092 Scene Harness — Dev-Gated HTTP Endpoint for Scenario Fixtures *(partial)*

**Observability (090, 103, 124, 132)**
- 090 OTEL Dashboard Restoration after Python Port · 103 Native OTEL via Tool Registry *(partial)* · 124 Save-Forensics Architecture — Read-Only Tiered Save Inspection, Loud-Skip Folds, and Per-Round Mechanical Census · 132 WatcherHub Infrastructure — builtins-Pinned Singleton, ContextVar Per-Session Isolation, and Ephemeral-Event Taxonomy

**Codebase Decomposition (060, 061, 062, 063, 064, 065, 068, 088)**
- 060 Genre Models Decomposition — Split models.rs by Domain · 061 Lore Module Decomposition — Split lore.rs by Responsibility · 062 Server lib.rs Extraction — Route Groups, State, and Watcher Events · 063 Dispatch Handler Splitting — By Pipeline Stage · 064 Game Crate Domain Modules — Organize 69 Flat Files · 065 Protocol Message Decomposition — Split message.rs by Domain *(deferred)* · 068 Magic Literal Extraction — Domain-Scoped Constants · **088 ADR Frontmatter Schema and Auto-Generated Indexes**

**Narrator Architecture (073, 076)**
- 073 Local Fine-Tuned Model Architecture · 076 Narration Protocol Collapse Post-TTS Removal

**Genre Mechanics (031, 033, 093, 099)**
- 031 Game Watcher — Semantic Telemetry for AI Agent Observability · 033 Genre Mechanics Engine — Confrontations & Resource Pools *(partial)* · 093 Confrontation Difficulty Calibration v1 · 099 Coyote Object Salvage Hooks — Two-Phase Auto-Fire for the_salvage *(deferred)*

**Project Lifecycle / Meta (082, 085, 087)**
- **082 Port `sidequest-api` from Rust back to Python** · **085 Tracker hygiene during the Rust→Python port — handling port-drift** · 087 Post-Port Subsystem Restoration Plan

**Conventions:** Bold = load-bearing for current architecture. `drift`/`partial`/`deferred` in a line means the ADR is accepted but implementation is not fully live — see [DRIFT.md](docs/adr/DRIFT.md). Superseded/historical ADRs are filtered from this view — see [SUPERSEDED.md](docs/adr/SUPERSEDED.md).

<!-- ADR-INDEX:GENERATED:END -->
