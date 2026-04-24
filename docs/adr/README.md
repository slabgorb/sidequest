# Architecture Decision Records

> Ported from sq-2 (Python), adapted for the Rust rewrite (~2026-03-30 to 2026-04-19),
> then carried back to Python per ADR-082.
> Game design decisions preserved across both language transitions.

## Port-era context

The backend was **Rust** (`sidequest-api`) from ~2026-03-30 to 2026-04-19, then
**ported back to Python** (`sidequest-server`) per **ADR-082**. Cutover completed
2026-04-23. The Rust tree is preserved read-only at
<https://github.com/slabgorb/sidequest-api> but no longer exists in the working
tree. **ADR-085** governed tracker hygiene through the port window.

### How to read older ADRs

Rust code samples and type declarations appear in ADRs throughout the 001–081
range — these were written while Rust was the live backend. Treat them as
**historical illustration**, not current implementation. The design decisions
carried forward; the language-specific mechanism descriptions did not. Quick
translation reference:

| Rust artifact in an ADR | Current Python reality |
|-------------------------|------------------------|
| `crates/sidequest-<X>/src/<Y>.rs` | `sidequest-server/sidequest/<X>/<Y>.py` |
| `#[derive(Serialize, Deserialize)] pub struct` | `class X(pydantic.BaseModel)` |
| `tokio::spawn`, `tokio::select!` | `asyncio.create_task`, `asyncio.wait` |
| `Arc<RwLock<T>>` | `asyncio.Lock` guarding a mutable |
| `rusqlite` | stdlib `sqlite3` (DB work via `asyncio.to_thread`) |
| `serde_yaml` | `pyyaml` |
| `axum` router | FastAPI app |
| `cargo test` | `pytest` |

Decomposition ADRs (060–065, 072) carry **"Post-port mapping"** notes at their
tails that translate crate layouts to the current Python package structure.
ADR-007 (character model) has a header note pointing to the Python home.
Narrative and game-system ADRs (014, 017–025, 041–043, etc.) describe
language-agnostic design and are unaffected by the port.

### ADRs whose status changed at cutover

The 2026-04-23 cutover audit moved these ADRs from `Proposed` to `Accepted`
because the Python port executed their plans:

- **ADR-060** (Genre Models Decomposition) — realized as `sidequest/genre/models/` package
- **ADR-061** (Lore Module Decomposition) — realized as sibling `lore_*.py` modules under `sidequest/game/`
- **ADR-062** (Server lib.rs Extraction) — realized as separate modules under `sidequest/server/`
- **ADR-063** (Dispatch Handler Splitting) — realized as `sidequest/server/dispatch/` package
- **ADR-064** (Game Crate Domain Modules) — *partially* accepted; most files flat, only `projection/` promoted to subdirectory
- **ADR-082** itself — moved from "Proposed (quick-look draft)" to `Accepted (cutover completed 2026-04-23)`

ADR-065 (protocol message decomposition) and ADR-072 (system/milieu split)
remain **Proposed** — the Python port did not execute them; the 1:1 port rule
forbade structural refactors during cutover.

Current backend reference documents: `docs/architecture.md`, `docs/tech-stack.md`,
`docs/api-contract.md`. An abbreviated index of this document is reproduced in
`CLAUDE.md` for agent activation context.

<!-- ADR-INDEX:GENERATED:BEGIN -->

> **Generated.** Do not edit this section by hand. Update frontmatter on the individual ADR files and rerun `scripts/regenerate_adr_indexes.py`. The preamble above the BEGIN marker and any prose below the END marker are preserved.

## Core Architecture

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-001: Claude CLI Only](001-claude-cli-only.md) | ✓ accepted | live |
| [ADR-002: SOUL Principles](002-soul-principles.md) | ✓ accepted | — |
| [ADR-003: Genre Pack Architecture](003-genre-pack-architecture.md) | ✓ accepted | live |
| [ADR-004: Lazy Genre Binding](004-lazy-genre-binding.md) | ✓ accepted | live |
| [ADR-005: Background-First Pipeline](005-background-first-pipeline.md) | ✓ accepted | live |
| [ADR-006: Graceful Degradation](006-graceful-degradation.md) | ✓ accepted | live |
| [ADR-007: Unified Character Model](007-unified-character-model.md) | ✓ accepted | live |

## Prompt Engineering

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-008: Three-Tier Rule Taxonomy](008-three-tier-prompt-taxonomy.md) | ✓ accepted | live |
| [ADR-009: Attention-Aware Prompt Zones](009-attention-aware-prompt-zones.md) | ✓ accepted | live |

## Agent System

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-011: World State JSON Patches](011-world-state-json-patches.md) | ✓ accepted | live |
| [ADR-012: Agent Session Management](012-agent-session-management.md) | ✓ accepted | live |
| [ADR-066: Persistent Opus Narrator Sessions](066-persistent-opus-narrator-sessions.md) | ✓ accepted | live |
| [ADR-067: Unified Narrator Agent — Collapse Multi-Agent into Single Persistent Session](067-unified-narrator-agent.md) | ✓ accepted | live |

## Game Systems

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-014: Diamonds and Coal](014-diamonds-and-coal.md) | ✓ accepted | — |
| [ADR-015: Character Builder State Machine](015-character-builder-state-machine.md) | ✓ accepted | live |
| [ADR-016: Three-Mode Character Creation](016-three-mode-chargen.md) | ✓ accepted | live |
| [ADR-018: Trope Engine](018-trope-engine.md) | ✓ accepted | **drift** → ADR-087 |
| [ADR-019: Cartography Discovery](019-cartography-discovery.md) | ✓ accepted | live |
| [ADR-020: NPC Disposition System](020-npc-disposition-system.md) | ✓ accepted | **drift** → ADR-087 |
| [ADR-021: Progression System](021-progression-system.md) | ✓ accepted | live |
| [ADR-022: WorldBuilder Maturity](022-world-builder-maturity.md) | ✓ accepted | live |
| [ADR-023: Session Persistence](023-session-persistence.md) | ✓ accepted | live |
| [ADR-024: Dual-Track Tension Model](024-dual-track-tension-model.md) | ✓ accepted | live |
| [ADR-025: Pacing Detection](025-pacing-detection.md) | ✓ accepted | live |
| [ADR-074: Dice Resolution Protocol — Player-Facing Rolls via WebSocket](074-dice-resolution-protocol.md) | ◇ proposed | deferred |
| [ADR-077: Dogfight Subsystem via StructuredEncounter Extension](077-dogfight-subsystem.md) | ◇ proposed | deferred → ADR-087 |
| [ADR-078: Edge / Composure Combat, Mechanical Advancement, and Push-Currency Rituals](078-edge-composure-advancement-rituals.md) | ◇ proposed | deferred → ADR-087 |
| [ADR-080: Unified Narrative Weight Trait](080-unified-narrative-weight-trait.md) | ✓ accepted | — |
| [ADR-081: Advancement Effect Variant Expansion (v1)](081-advancement-effect-variant-expansion.md) | ◇ proposed | deferred → ADR-087 |

## Frontend / Protocol

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-026: Client-Side State Mirror](026-client-state-mirror.md) | ✓ accepted | live |
| [ADR-027: Reactive State Messaging](027-reactive-state-messaging.md) | ✓ accepted | live |
| [ADR-075: 3D Dice Rendering — Three.js + Rapier Physics Overlay](075-3d-dice-rendering.md) | ◇ proposed | deferred |
| [ADR-079: Genre Theme System Unification](079-genre-theme-unification.md) | ✓ accepted | live |

## Multiplayer

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-028: Perception Rewriter](028-perception-rewriter.md) | ✓ accepted | live |
| [ADR-029: Guest NPC Players](029-guest-npc-players.md) | ◇ proposed | deferred |
| [ADR-030: Scenario Packs](030-scenario-packs.md) | ◇ proposed | deferred |
| [ADR-036: Multiplayer Turn Coordination](036-multiplayer-turn-coordination.md) | ✓ accepted | live |
| [ADR-037: Shared-World / Per-Player State Split](037-shared-world-per-player-state.md) | ✓ accepted | live |

## Transport / Infrastructure

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-035: Unix Socket IPC for Python Sidecar](035-unix-socket-ipc-sidecar.md) | ✓ accepted | live |
| [ADR-038: WebSocket Transport Architecture](038-websocket-transport-architecture.md) | ✓ accepted | live |
| [ADR-046: GPU Memory Budget Coordinator](046-gpu-memory-budget-coordinator.md) | ✓ accepted | live |
| [ADR-047: Prompt Injection Sanitization Layer](047-prompt-injection-sanitization.md) | ✓ accepted | live |

## Narrator / Text

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-040: Narrative Character Sheet (No Raw Stats)](040-narrative-character-sheet.md) | ✓ accepted | live |
| [ADR-049: Narrator Verbosity and Vocabulary (Two-Axis Text Tuning)](049-narrator-verbosity-vocabulary.md) | ✓ accepted | live |
| [ADR-052: Narrative Axis System (/tone Command)](052-narrative-axis-system.md) | ✓ accepted | live |
| [ADR-057: Narrator Crunch Separation — LLM Narrates, Scripts Crunch](057-narrator-crunch-separation.md) | ✓ accepted | *partial* → ADR-059 |

## NPC / Character Systems

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-041: Genie Wish / Consequence Engine](041-genie-wish-consequence-engine.md) | ✓ accepted | **drift** → ADR-087 |
| [ADR-042: OCEAN Personality Live Evolution](042-ocean-personality-live-evolution.md) | ✓ accepted | **drift** → ADR-087 |
| [ADR-043: Conlang Morpheme System](043-conlang-morpheme-system.md) | ✓ accepted | **drift** → ADR-087 |
| [ADR-053: Scenario System (Clue Graph, Belief State, Gossip Propagation)](053-scenario-system.md) | ✓ accepted | **drift** → ADR-087 |

## Media / Audio / Rendering

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-044: Speculative Prerendering During TTS Playback](044-speculative-prerendering.md) | ✓ accepted | **drift** → ADR-087 |
| [ADR-045: Client Audio Engine](045-client-audio-engine.md) | ✓ accepted | *partial* → ADR-076 |
| [ADR-048: Lore RAG Store with Cross-Process Embedding](048-lore-rag-store.md) | ✓ accepted | live |
| [ADR-050: Image Pacing Throttle](050-image-pacing-throttle.md) | ✓ accepted | live |
| [ADR-070: MLX Image Renderer — Replace PyTorch/diffusers with Apple MLX](070-mlx-image-renderer.md) | ✓ accepted | live |
| [ADR-083: Multi-LoRA Stacking and Verification Pipeline](083-multi-lora-stacking-and-verification.md) | ◇ proposed | deferred |
| [ADR-086: Image-Composition Taxonomy — Portraits, POIs, Illustrations](086-image-composition-taxonomy.md) | ◇ proposed | deferred |

## Turn Management

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-051: Two-Tier Turn Counter (Interaction vs. Round)](051-two-tier-turn-counter.md) | ✓ accepted | live |

## Room Graph / Dungeon Crawl

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-055: Room Graph Navigation](055-room-graph-navigation.md) | ◇ proposed | deferred |

## Code Generation / Tooling

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-059: Monster Manual — Server-Side Pre-Generation via Game-State Injection](059-monster-manual-server-side-pregen.md) | ✓ accepted | **drift** → ADR-087 |
| [ADR-069: Scenario Fixtures — Pre-configured World States for Testing](069-scenario-fixtures.md) | ✓ accepted | **drift** → ADR-087 |

## Observability

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-058: Claude Subprocess OTEL Passthrough](058-claude-subprocess-otel-passthrough.md) | ◇ proposed | deferred |

## Codebase Decomposition

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-060: Genre Models Decomposition — Split models.rs by Domain](060-genre-models-decomposition.md) | ✓ accepted | live |
| [ADR-061: Lore Module Decomposition — Split lore.rs by Responsibility](061-lore-module-decomposition.md) | ✓ accepted | live |
| [ADR-062: Server lib.rs Extraction — Route Groups, State, and Watcher Events](062-server-lib-extraction.md) | ✓ accepted | live |
| [ADR-063: Dispatch Handler Splitting — By Pipeline Stage](063-dispatch-handler-splitting.md) | ✓ accepted | live |
| [ADR-064: Game Crate Domain Modules — Organize 69 Flat Files](064-game-crate-domain-modules.md) | ✓ accepted | live |
| [ADR-065: Protocol Message Decomposition — Split message.rs by Domain](065-protocol-message-decomposition.md) | ◇ proposed | deferred |
| [ADR-068: Magic Literal Extraction — Domain-Scoped Constants](068-magic-literal-extraction.md) | ✓ accepted | live |
| [ADR-072: System/Milieu Decomposition — Separating Mechanics from Aesthetic](072-system-milieu-decomposition.md) | ◇ proposed | deferred |
| [ADR-088: ADR Frontmatter Schema and Auto-Generated Indexes](088-adr-frontmatter-schema.md) | ✓ accepted | live |

## Narrator Architecture

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-073: Local Fine-Tuned Model Architecture](073-local-fine-tuned-model-architecture.md) | ✓ accepted | live |
| [ADR-076: Narration Protocol Collapse Post-TTS Removal](076-narration-protocol-collapse-post-tts.md) | ◇ proposed | deferred |

## Genre Mechanics

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-031: Game Watcher — Semantic Telemetry for AI Agent Observability](031-game-watcher-semantic-telemetry.md) | ✓ accepted | live |
| [ADR-033: Genre Mechanics Engine — Confrontations & Resource Pools](033-confrontation-engine-resource-pools.md) | ✓ accepted | *partial* → ADR-087 |

## Project Lifecycle / Meta

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-082: Port `sidequest-api` from Rust back to Python](082-port-api-rust-to-python.md) | ✓ accepted | live |
| [ADR-085: Tracker hygiene during the Rust→Python port — handling port-drift](085-rust-to-python-port-drift.md) | ✓ accepted | live |
| [ADR-087: Post-Port Subsystem Restoration Plan](087-post-port-subsystem-restoration-plan.md) | ◇ proposed | deferred |

## Superseded / Historical

Retired ADRs. See [SUPERSEDED.md](SUPERSEDED.md) for the grouped view.

| ADR | Status | Successor |
|-----|--------|-----------|
| [ADR-010: Intent-Based Agent Routing](010-intent-based-agent-routing.md) | ✗ superseded | [ADR-067](067-unified-narrator-agent.md) |
| [ADR-013: Lazy JSON Extraction](013-lazy-json-extraction.md) | ✗ superseded | [ADR-057](057-narrator-crunch-separation.md) |
| [ADR-017: Cinematic Chase Engine](017-cinematic-chase-engine.md) | ✗ superseded | [ADR-033](033-confrontation-engine-resource-pools.md) |
| [ADR-032: Genre-Specific LoRA Style Training for Flux Image Generation](032-genre-lora-style-training.md) | ✗ superseded | [ADR-070](070-mlx-image-renderer.md) |
| [ADR-034: Portrait Identity Consistency — Tiered Character Recognition Pipeline](034-portrait-identity-consistency.md) | ✗ superseded | [ADR-086](086-image-composition-taxonomy.md) |
| [ADR-039: Narrator Structured Output (JSON Sidecar Block)](039-narrator-structured-output.md) | ✗ superseded | [ADR-057](057-narrator-crunch-separation.md) |
| [ADR-054: WebRTC Voice Chat (Disabled — Echo Feedback Loop)](054-webrtc-voice-chat-disabled.md) | ✗ historical | — |
| [ADR-056: Script Tool Generators — Offloading Structured Generation from LLM to Rust Binaries](056-script-tool-generators.md) | ✗ superseded | [ADR-059](059-monster-manual-server-side-pregen.md) |
| [ADR-071: Tactical ASCII Grid Maps — Deterministic Room Layout via ASCII Art](071-tactical-ascii-grid-maps.md) | ✗ superseded | [ADR-086](086-image-composition-taxonomy.md) |
| [ADR-084: Compositional-Dimension Specialization for Style LoRAs](084-lora-composition-dimension.md) | ✗ superseded | [ADR-070](070-mlx-image-renderer.md) |

## Implementation Drift

ADRs whose implementation is absent, partial, or deferred. See [DRIFT.md](DRIFT.md) for priority-tier details.

| ADR | Impl | Pointer |
|-----|------|---------|
| [ADR-029: Guest NPC Players](029-guest-npc-players.md) | deferred | — |
| [ADR-030: Scenario Packs](030-scenario-packs.md) | deferred | — |
| [ADR-055: Room Graph Navigation](055-room-graph-navigation.md) | deferred | — |
| [ADR-058: Claude Subprocess OTEL Passthrough](058-claude-subprocess-otel-passthrough.md) | deferred | — |
| [ADR-065: Protocol Message Decomposition — Split message.rs by Domain](065-protocol-message-decomposition.md) | deferred | — |
| [ADR-072: System/Milieu Decomposition — Separating Mechanics from Aesthetic](072-system-milieu-decomposition.md) | deferred | — |
| [ADR-074: Dice Resolution Protocol — Player-Facing Rolls via WebSocket](074-dice-resolution-protocol.md) | deferred | — |
| [ADR-075: 3D Dice Rendering — Three.js + Rapier Physics Overlay](075-3d-dice-rendering.md) | deferred | — |
| [ADR-076: Narration Protocol Collapse Post-TTS Removal](076-narration-protocol-collapse-post-tts.md) | deferred | — |
| [ADR-077: Dogfight Subsystem via StructuredEncounter Extension](077-dogfight-subsystem.md) | deferred | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-078: Edge / Composure Combat, Mechanical Advancement, and Push-Currency Rituals](078-edge-composure-advancement-rituals.md) | deferred | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-081: Advancement Effect Variant Expansion (v1)](081-advancement-effect-variant-expansion.md) | deferred | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-083: Multi-LoRA Stacking and Verification Pipeline](083-multi-lora-stacking-and-verification.md) | deferred | — |
| [ADR-086: Image-Composition Taxonomy — Portraits, POIs, Illustrations](086-image-composition-taxonomy.md) | deferred | — |
| [ADR-087: Post-Port Subsystem Restoration Plan](087-post-port-subsystem-restoration-plan.md) | deferred | — |
| [ADR-018: Trope Engine](018-trope-engine.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-020: NPC Disposition System](020-npc-disposition-system.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-041: Genie Wish / Consequence Engine](041-genie-wish-consequence-engine.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-042: OCEAN Personality Live Evolution](042-ocean-personality-live-evolution.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-043: Conlang Morpheme System](043-conlang-morpheme-system.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-044: Speculative Prerendering During TTS Playback](044-speculative-prerendering.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-053: Scenario System (Clue Graph, Belief State, Gossip Propagation)](053-scenario-system.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-059: Monster Manual — Server-Side Pre-Generation via Game-State Injection](059-monster-manual-server-side-pregen.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-069: Scenario Fixtures — Pre-configured World States for Testing](069-scenario-fixtures.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-033: Genre Mechanics Engine — Confrontations & Resource Pools](033-confrontation-engine-resource-pools.md) | *partial* | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-045: Client Audio Engine](045-client-audio-engine.md) | *partial* | [ADR-076](076-narration-protocol-collapse-post-tts.md) |
| [ADR-057: Narrator Crunch Separation — LLM Narrates, Scripts Crunch](057-narrator-crunch-separation.md) | *partial* | [ADR-059](059-monster-manual-server-side-pregen.md) |

<!-- ADR-INDEX:GENERATED:END -->
