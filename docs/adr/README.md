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
| [Intent-Based Agent Routing](010-intent-based-agent-routing.md) | **Superseded by ADR-067** | LLM classifier routed player input to specialist agents (historical) |
| [World State JSON Patches](011-world-state-json-patches.md) | Accepted | Agents emit patches, not full state replacements |
| [Agent Session Management](012-agent-session-management.md) | Accepted | Persistent Claude sessions with stale recovery |
| [Lazy JSON Extraction](013-lazy-json-extraction.md) | Superseded by ADR-057 | Three-tier fallback replaced by sidecar tool calls |

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
| [Dice Resolution Protocol](074-dice-resolution-protocol.md) | Proposed | Server-authoritative dice rolls via WebSocket with sealed-letter integration |
| [Dogfight Subsystem](077-dogfight-subsystem.md) | Proposed | StructuredEncounter extension for sealed-letter fighter duels (per-actor descriptors + cross-product lookup table) |
| [Edge / Composure + Mechanical Advancement + Push-Currency Rituals](078-edge-composure-advancement-rituals.md) | Proposed | Replace phantom HP with first-class `EdgePool` on `CreatureCore`; first hard link from ADR-021 progression to engine state; extend `pact_working` beats with `resource_deltas` for push-currency spellcraft |
| [Unified Narrative Weight Trait](080-unified-narrative-weight-trait.md) | Accepted | ADR-014 enforcement — `NarrativeWeight` newtype + `Weighted` trait unifies weight across inventory, tropes, beats, scenes, NPCs, encounters |
| [Advancement Effect Variant Expansion (v1)](081-advancement-effect-variant-expansion.md) | Proposed | Adds `AllyEdgeIntercept` + `ConditionalEffectGating` variants to ADR-078's `AdvancementEffect` enum for Prot'Thokk's *Lil' Sebastian Stands* and Th`rook's *The Dose Helps* |

## Frontend / Protocol

| ADR | Status | Summary |
|-----|--------|---------|
| [Client-Side State Mirror](026-client-state-mirror.md) | Accepted | Server piggybacks state deltas; slash commands resolve locally |
| [Reactive State Messaging](027-reactive-state-messaging.md) | Accepted | State changes emit typed events to connected clients |
| [3D Dice Rendering](075-3d-dice-rendering.md) | Proposed | Three.js + Rapier overlay with genre-themed skins and deterministic replay |
| [Genre Theme Unification](079-genre-theme-unification.md) | Accepted | Single-source genre CSS with `:root[data-genre]` specificity; kill ThemeProvider and JS bridge |

## Multiplayer

| ADR | Status | Summary |
|-----|--------|---------|
| [Perception Rewriter](028-perception-rewriter.md) | Accepted | Per-player narrative rewriting based on status effects |
| [Guest NPC Players](029-guest-npc-players.md) | Proposed | Guest players control consequential NPCs |
| [Scenario Packs](030-scenario-packs.md) | Proposed | Hidden-role scenario engine with clue DAGs |
| [Multiplayer Turn Coordination](036-multiplayer-turn-coordination.md) | Accepted | Three-mode FSM with adaptive barrier and claim-election |
| [Shared-World / Per-Player State](037-shared-world-per-player-state.md) | Accepted | SharedGameSession keyed by genre:world, sync-to-locals pattern |
| [WebRTC Voice Chat (Disabled)](054-webrtc-voice-chat-disabled.md) | Historical | Was disabled for echo feedback; WebRTC + Whisper files since **deleted** along with TTS removal |

## Transport / Infrastructure

| ADR | Status | Summary |
|-----|--------|---------|
| [Unix Socket IPC for Python Sidecar](035-unix-socket-ipc-sidecar.md) | Accepted | Rust/Python split via Unix socket JSON-RPC, daemon stays warm |
| [WebSocket Transport Architecture](038-websocket-transport-architecture.md) | Accepted | Reader/writer split, three broadcast channels, ProcessingGuard |
| [Prompt Injection Sanitization](047-prompt-injection-sanitization.md) | Accepted | Protocol-layer sanitization of all player text before agent prompts |
| [GPU Memory Budget Coordinator](046-gpu-memory-budget-coordinator.md) | Accepted | LRU eviction across ML models on 80GB Apple Silicon budget |

## Narrator / Text

| ADR | Status | Summary |
|-----|--------|---------|
| [Narrator Structured Output](039-narrator-structured-output.md) | Accepted | JSON sidecar block — all extractions in single parse pass |
| [Narrator Verbosity × Vocabulary](049-narrator-verbosity-vocabulary.md) | Accepted | Two orthogonal axes for text length and diction complexity |
| [Narrative Character Sheet](040-narrative-character-sheet.md) | Accepted | No raw stats exposed — all values narrated through genre voice |
| [Narrative Axis System](052-narrative-axis-system.md) | Accepted | Data-driven /tone command with genre-defined axes and presets |

## NPC / Character Systems

| ADR | Status | Summary |
|-----|--------|---------|
| [Genie Wish / Consequence Engine](041-genie-wish-consequence-engine.md) | Accepted | "Yes, and" power-grab handling with rotating consequence types |
| [OCEAN Personality Live Evolution](042-ocean-personality-live-evolution.md) | Accepted | Narrator-extracted events shift NPC personality profiles in play |
| [Conlang Morpheme System](043-conlang-morpheme-system.md) | Accepted | Seeded procedural naming with morphological root consistency |
| [Scenario System](053-scenario-system.md) | Accepted | Clue DAG, belief state, gossip propagation, accusation evaluator |

## Media / Audio / Rendering

| ADR | Status | Summary |
|-----|--------|---------|
| [Speculative Prerendering](044-speculative-prerendering.md) | Accepted | Latency-hiding image renders queued against turn boundaries (originally "during TTS playback") |
| [Client Audio Engine](045-client-audio-engine.md) | Partially superseded | Web Audio graph now two-channel (music + SFX) after TTS removal; Crossfader still active |
| [Image Pacing Throttle](050-image-pacing-throttle.md) | Accepted | Configurable cooldown with DM force-override, separate from BeatFilter |
| [Lore RAG Store](048-lore-rag-store.md) | Accepted | Cross-process embedding pipeline with budget-aware context selection |
| [MLX Image Renderer](070-mlx-image-renderer.md) | Accepted | Replace PyTorch/diffusers Flux worker with Apple MLX runtime |
| [Multi-LoRA Stacking and Verification Pipeline](083-multi-lora-stacking-and-verification.md) | Proposed | Hybrid genre + world LoRA stack with extend/exclude/add merge; MLX-native training + custom remapper; SSIM pre-promotion gate + runtime `matched_key_count` OTEL |

## Turn Management

| ADR | Status | Summary |
|-----|--------|---------|
| [Two-Tier Turn Counter](051-two-tier-turn-counter.md) | Accepted | Interaction (monotonic) vs Round (narrative beats) separation |

## Room Graph / Dungeon Crawl

| ADR | Status | Summary |
|-----|--------|---------|
| [Room Graph Navigation](055-room-graph-navigation.md) | Accepted | Graph-based dungeon navigation with resource pressure |
| [Tactical ASCII Grid Maps](071-tactical-ascii-grid-maps.md) | Proposed | Deterministic room layout via ASCII art for tactical play |

## Code Generation / Tooling

| ADR | Status | Summary |
|-----|--------|---------|
| [Script Tool Generators](056-script-tool-generators.md) | Accepted | Offload structured generation from LLM to Rust CLI binaries |
| [Monster Manual — Server-Side Pre-Generation](059-monster-manual-server-side-pregen.md) | Accepted | Pre-gen NPCs/encounters via Rust tools, inject into game_state |
| [Scenario Fixtures](069-scenario-fixtures.md) | Accepted | Pre-configured world states for testing |

## Narrator Architecture

| ADR | Status | Summary |
|-----|--------|---------|
| [Narrator Crunch Separation](057-narrator-crunch-separation.md) | Accepted | LLM narrates prose, sidecar tools handle mechanical state |
| [Persistent Opus Narrator Sessions](066-persistent-opus-narrator-sessions.md) | Accepted | Long-lived Opus sessions for narrator continuity |
| [Unified Narrator Agent](067-unified-narrator-agent.md) | Accepted (migration in progress) | Collapse multi-agent into single persistent session — `intent_router` still resident |
| [Local Fine-Tuned Model Architecture](073-local-fine-tuned-model-architecture.md) | Accepted | Local fine-tuned model plan to replace generic Claude prompting for narrator |
| [Narration Protocol Collapse Post-TTS](076-narration-protocol-collapse-post-tts.md) | Proposed | Remove `NarrationChunk` and TTS-era UI buffer plumbing |

## Observability

| ADR | Status | Summary |
|-----|--------|---------|
| [Claude Subprocess OTEL Passthrough](058-claude-subprocess-otel-passthrough.md) | Accepted | See inside Claude CLI subprocess calls via OTEL spans |

## Codebase Decomposition

| ADR | Status | Summary |
|-----|--------|---------|
| [Genre Models Decomposition](060-genre-models-decomposition.md) | Accepted | Split models.rs by domain |
| [Lore Module Decomposition](061-lore-module-decomposition.md) | Accepted | Split lore.rs by responsibility |
| [Server lib.rs Extraction](062-server-lib-extraction.md) | Accepted | Route groups, state, and watcher events |
| [Dispatch Handler Splitting](063-dispatch-handler-splitting.md) | Accepted | Split dispatch by pipeline stage |
| [Game Crate Domain Modules](064-game-crate-domain-modules.md) | Accepted | Organize flat files into domain modules |
| [Protocol Message Decomposition](065-protocol-message-decomposition.md) | Proposed (unexecuted) | Plan to split message.rs by domain; `message.rs` remains a single file |
| [Magic Literal Extraction](068-magic-literal-extraction.md) | Accepted | Domain-scoped constants replace magic literals |
| [System/Milieu Decomposition](072-system-milieu-decomposition.md) | Proposed | Split genre packs into mechanics (system), aesthetic (milieu), and world instances |

## Media Pipeline (stays in sidequest-daemon)

These decisions govern the Python media daemon, not the Rust API. Listed here
for reference — the daemon is a separate repo (`sidequest-daemon`).

| ADR | Origin | Status | Summary |
|-----|--------|--------|---------|
| Renderer Daemon | sq-2 | Active | Persistent daemon with Unix socket and multi-model GPU pool |
| Flux Worker | sq-2 | Active | Schnell for text overlays, dev for scene art and cartography |
| Scene Interpreter | sq-2 | Active | Pattern-matching narrative text to structured stage cues |
| Pre-Generated Audio | sq-2 | Active | ACE-Step at build time, library playback at runtime |
| Thematic Audio Variations | sq-2 | Active | Theme families with mood-intensity variation selection |
| Kokoro TTS | sq-2 | **Removed (2026-04)** | Was Kokoro primary + Piper fallback; the entire TTS path has been removed — see ADR-076 |
| Scene Cache | sq-2 | Active | SHA256-keyed LRU render cache on disk |
| Subject Extractor | sq-2 | Active | Claude CLI translates prose to visual descriptions |
| Beat Filter | sq-2 | Active | Heuristic gate for image generation worthiness |
| Library Backend | sq-2 | Active | DJ/radio separation for audio track selection vs playback |
| Stale Render Policy | sq-2 | Active | Only TEXT_OVERLAY tier is discardable after scene change |
| Music Director Agent | sq-2 | Active | LLM selects music by narrative mood, not heuristics |

## Project Lifecycle / Meta

| ADR | Status | Summary |
|-----|--------|---------|
| [Port API Rust to Python](082-port-api-rust-to-python.md) | Accepted | Port `sidequest-api` back to Python as `sidequest-server`; Rust tree becomes read-only spec |
| [LoRA Composition Dimension](084-lora-composition-dimension.md) | Proposed | Composition axis separate from genre/world LoRA stacking |
| [Rust→Python Port-Drift Tracker Hygiene](085-rust-to-python-port-drift.md) | Accepted | Sprint-tracker status reflects live Python backend, not Rust archive; audit procedure for in-flight epics |

## Skipped (superseded or not applicable)

- ~~Discord Multiplayer~~ — superseded by WebSocket server
- ~~Illustrated Book TUI~~ — superseded by React client
- ~~Custom Game Client~~ — superseded by React client
- ~~Voice Pipeline Dual Engine~~ — was superseded by Kokoro TTS; all voice synthesis now removed from the system (2026-04)
- ~~React Web Client~~ — describes the UI we already have (see api-contract.md)
- ~~RAG Lore Retrieval~~ — implemented as [Lore RAG Store](048-lore-rag-store.md) using daemon embeddings
- ~~Inter-Agent Channel~~ — minimal usage; replaced by in-memory channels in Rust
- ~~TDD Enforcement Tests~~ — process doc, not architecture
