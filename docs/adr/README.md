# Architecture Decision Records

> Ported from sq-2 (Python) and adapted for the Rust rewrite.
> Language-specific details updated; game design decisions preserved.

## Core Architecture

| ADR | Status | Summary |
|-----|--------|---------|
| [Claude CLI Only](001-claude-cli-only.md) | Accepted | All LLM calls via `claude -p` subprocess, no Anthropic SDK |
| [SOUL Principles](002-soul-principles.md) | Accepted | SOUL.md parsed and injected into every agent prompt |
| [Genre Pack Architecture](003-genre-pack-architecture.md) | Accepted | Swappable YAML directories configure all game systems |
| [Lazy Genre Binding](004-lazy-genre-binding.md) | Accepted | Server starts genre-agnostic; genre bound at runtime on connect |
| [Background-First Pipeline](005-background-first-pipeline.md) | Accepted | Only text response is critical path; everything else spawns |
| [Graceful Degradation](006-graceful-degradation.md) | Accepted | Fallback chains across all subsystems |
| [Unified Character Model](007-unified-character-model.md) | Accepted | Narrative identity + mechanical stats in one struct |

## Prompt Engineering

| ADR | Status | Summary |
|-----|--------|---------|
| [Three-Tier Rule Taxonomy](008-three-tier-prompt-taxonomy.md) | Accepted | Critical/Firm/Coherence rules with genre pack overrides |
| [Attention-Aware Prompt Zones](009-attention-aware-prompt-zones.md) | Accepted | EARLY/VALLEY/LATE zones position content by attention priority |

## Agent System

| ADR | Status | Summary |
|-----|--------|---------|
| [Intent-Based Agent Routing](010-intent-based-agent-routing.md) | Accepted | LLM classifier routes player input to specialist agents |
| [World State JSON Patches](011-world-state-json-patches.md) | Accepted | Agents emit patches, not full state replacements |
| [Agent Session Management](012-agent-session-management.md) | Accepted | Persistent Claude sessions with stale recovery |
| [Lazy JSON Extraction](013-lazy-json-extraction.md) | Accepted | Three-tier fallback for parsing Claude subprocess output |

## Game Systems

| ADR | Status | Summary |
|-----|--------|---------|
| [Diamonds and Coal](014-diamonds-and-coal.md) | Accepted | `narrative_weight` scales detail across all output systems |
| [Character Builder State Machine](015-character-builder-state-machine.md) | Accepted | Genre-driven scene-based creation with narrative hooks |
| [Three-Mode Character Creation](016-three-mode-chargen.md) | Accepted | Menu, guided, and freeform creation — same Character output |
| [Cinematic Chase Engine](017-cinematic-chase-engine.md) | Accepted | Beat-based chases with Lead variable and rig mechanics |
| [Trope Engine](018-trope-engine.md) | Accepted | Genre-defined narrative pacing via trope lifecycle |
| [Cartography Discovery](019-cartography-discovery.md) | Accepted | Graph-based world topology with origin-seeded fog of war |
| [NPC Disposition System](020-npc-disposition-system.md) | Accepted | Numeric disposition with qualitative attitude derivation |
| [Progression System](021-progression-system.md) | Accepted | Four tracks: milestones, affinities, item evolution, wealth |
| [WorldBuilder Maturity](022-world-builder-maturity.md) | Accepted | Campaign maturity states for in medias res starts |
| [Session Persistence](023-session-persistence.md) | Accepted | State + narrative log with "Previously On..." recap |
| [Dual-Track Tension Model](024-dual-track-tension-model.md) | Accepted | drama_weight from gambler's ramp + HP stakes + event spikes |
| [Pacing Detection](025-pacing-detection.md) | Accepted | Quiet turn counting + trope-aware escalation hints |

## Frontend / Protocol

| ADR | Status | Summary |
|-----|--------|---------|
| [Client-Side State Mirror](026-client-state-mirror.md) | Accepted | Server piggybacks state deltas; slash commands resolve locally |
| [Reactive State Messaging](027-reactive-state-messaging.md) | Accepted | State changes emit typed events to connected clients |

## Multiplayer

| ADR | Status | Summary |
|-----|--------|---------|
| [Perception Rewriter](028-perception-rewriter.md) | Accepted | Per-player narrative rewriting based on status effects |
| [Guest NPC Players](029-guest-npc-players.md) | Proposed | Guest players control consequential NPCs |
| [Scenario Packs](030-scenario-packs.md) | Proposed | Hidden-role scenario engine with clue DAGs |

## Media Pipeline (stays in sidequest-daemon)

These decisions govern the Python media daemon, not the Rust API. Listed here
for reference — the daemon is a separate repo (`sidequest-daemon`).

| ADR | Origin | Summary |
|-----|--------|---------|
| Renderer Daemon | sq-2 | Persistent daemon with Unix socket and multi-model GPU pool |
| Flux Worker | sq-2 | Schnell for text overlays, dev for scene art and cartography |
| Scene Interpreter | sq-2 | Pattern-matching narrative text to structured stage cues |
| Pre-Generated Audio | sq-2 | ACE-Step at build time, library playback at runtime |
| Thematic Audio Variations | sq-2 | Theme families with mood-intensity variation selection |
| Kokoro TTS | sq-2 | Kokoro primary (54 voices, streaming) + Piper fallback |
| Scene Cache | sq-2 | SHA256-keyed LRU render cache on disk |
| Subject Extractor | sq-2 | Claude CLI translates prose to visual descriptions |
| Beat Filter | sq-2 | Heuristic gate for image generation worthiness |
| Library Backend | sq-2 | DJ/radio separation for audio track selection vs playback |
| Stale Render Policy | sq-2 | Only TEXT_OVERLAY tier is discardable after scene change |
| Music Director Agent | sq-2 | LLM selects music by narrative mood, not heuristics |

## Skipped (superseded or not applicable)

- ~~Discord Multiplayer~~ — superseded by WebSocket server
- ~~Illustrated Book TUI~~ — superseded by React client
- ~~Custom Game Client~~ — superseded by React client
- ~~Voice Pipeline Dual Engine~~ — superseded by Kokoro TTS
- ~~React Web Client~~ — describes the UI we already have (see api-contract.md)
- ~~RAG Lore Retrieval~~ — deferred (requires sqlite-vec + embeddings; revisit later)
- ~~Inter-Agent Channel~~ — minimal usage; replaced by in-memory channels in Rust
- ~~TDD Enforcement Tests~~ — process doc, not architecture
