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
| [ADR-002: SOUL Principles](002-soul-principles.md) | ✓ accepted | live |
| [ADR-003: Genre Pack Architecture](003-genre-pack-architecture.md) | ✓ accepted | live |
| [ADR-004: Lazy Genre Binding](004-lazy-genre-binding.md) | ✓ accepted | live |
| [ADR-005: Background-First Pipeline](005-background-first-pipeline.md) | ✓ accepted | live |
| [ADR-006: Graceful Degradation](006-graceful-degradation.md) | ✓ accepted | live |
| [ADR-007: Unified Character Model](007-unified-character-model.md) | ✓ accepted | live |
| [ADR-101: Anthropic SDK as Narrator Backend](101-anthropic-sdk-as-narrator-backend.md) | ✓ accepted | *partial* → Backend live + default on develop: sidequest-server/sidequest/agents/llm_factory.py (default anthropic_sdk), anthropic_sdk_client.py, model_routing.py, anthropic_cost.py. Phased cleanups (sidecar/perception-rewriter/OTEL-scraper deletion) tracked by ADR-102/104/103. |
| [ADR-115: Persistence Substrate Migration — SQLite-Per-Session to PostgreSQL](115-postgres-persistence-substrate.md) | ✓ accepted | live → docs/superpowers/specs/2026-05-26-postgres-persistence-migration-design.md |
| [ADR-121: Layered Content Resolution — Per-Field Merge Strategies and Provenance; the Two-Tier Archetype Shim Is the Production Path](121-layered-content-resolution.md) | ✓ accepted | live → LayeredMerge/MergeStrategy (genre/resolver.py) + provenance wire types (protocol/provenance.py) + two-tier shim (genre/archetype/shim.py via chargen_mixin); four-tier Resolver walk removed by story 82-4 |
| [ADR-135: Reference Pages Are a Public Table Tool — Single Fixed Projection, No GM Audience](135-reference-pages-public-table-tool.md) | ✓ accepted | *partial* → sidequest-server reference_renderer.py — audience doctrine + stories 65-7..65-9 live; 65-10..65-12 pending. The 2026-06-08 amendment (server-projection / React-render seam) reframes the render substrate from server HTML to a projected JSON API + React SPA — design-only, implementation tracked as epic 100; see the Amendment section and docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md. |
| [ADR-140: Genre Is the Rulebook Only; the World Owns the Cast and Catalog — Supersedes ADR-120's Mechanics-in-Genre](140-genre-rulebook-world-cast-catalog.md) | ✓ accepted | *partial* → sidequest-server/sidequest/genre/loader.py (_load_single_world world-tier classes/spells_wwn/seed_tropes loads + pack-level world-first aggregation), sidequest/server/dispatch/{class_resolve,char_creation_resolve,wwn_spell_catalog_resolve}.py (world-first resolvers), sidequest/genre/models/pack.py (World.classes / World.wwn_spell_catalog / World.chassis_classes / World.seed_tropes). Delivered by epic 94 stories 94-1..94-3. |

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
| [ADR-013: Lazy JSON Extraction](013-lazy-json-extraction.md) | ✓ accepted | **drift** → ADR-102 |
| [ADR-067: Unified Narrator Agent — Collapse Multi-Agent into Single Narrator](067-unified-narrator-agent.md) | ✓ accepted | live |
| [ADR-098: Stateless Narrator Turns — Drop --resume, Bounded Per-Turn Prompts](098-stateless-narrator-turns.md) | ✓ accepted | live |
| [ADR-100: Journal Pipeline Coherence — Footnotes, KnownFacts, JOURNAL_RESPONSE, and the Scenario Clue Hook](100-journal-pipeline-coherence.md) | ✓ accepted | live → sidequest-server/sidequest/server/websocket_session_handler.py (consume_clue_footnotes) + handlers/journal_request.py (JOURNAL_REQUEST) + ui useStateMirror.ts |
| [ADR-102: Tool-Use Protocol for Structured Output](102-tool-use-protocol-for-structured-output.md) | ✓ accepted | *partial* → ADR-101 |
| [ADR-110: Game-State Snapshot Slimming — Compact Encoding + Allowlist Pruning, Diff-with-Anchor Deferred](110-game-state-snapshot-slimming.md) | ✓ accepted | *partial* → sidequest-server/sidequest/server/session_helpers.py#_PHASE_B_DROP_FIELDS |
| [ADR-111: Recency-Zone Narrator Guardrails Migrate to Tool Descriptions and Primacy-Cached Output Prose](111-narrator-guardrails-into-tool-descriptions.md) | ✓ accepted | live → sidequest-server/sidequest/agents/narrator_guardrails.py + orchestrator.py guardrail registration + intent_router.py CONFRONTATION_TRIGGER_CORE |
| [ADR-112: Genre Prose Cache Promotion — Four Always-Fire Session-Static Sections Move to Stable, Conditional Sections Defer](112-genre-prose-stable-cache-promotion.md) | ✓ accepted | *partial* → sprint/current-sprint.yaml#57-3 |
| [ADR-113: Intent Router — Mechanical-Engagement Spine](113-intent-router-mechanical-engagement-spine.md) | ✓ accepted | live → sidequest-server intent_router.py + run_dispatch_bank confidence gate (story 71-16, default 0.6, RulesConfig.dispatch_confidence_thresholds) |
| [ADR-118: Universal Retrieval Layer — Index + Per-Turn Floor-and-Fill Retrieval for NPCs, Locations, and Factions](118-universal-retrieval-layer.md) | ✓ accepted | live → Core (D1–D5) live: sidequest-server/sidequest/game/retrieval_orchestration.py + entity_card.py + dispatch/universal_retrieval.py — retrieve_turn_context called every narrator turn. The 2026-06-04 amendment (unified pertinence scorer / lifecycle-aware scope / tiered forgetting) is design-only — implementation pending; see the Amendment section. |
| [ADR-123: Mechanical-Engagement Pipeline — Confidence-Gated Topological Dispatch Bank, Precondition/Unregistered Gates, and the LethalityArbiter](123-mechanical-engagement-pipeline.md) | ✓ accepted | live |
| [ADR-134: Per-Session API Cost Runaway Detector and Hard-Kill Ceiling — Rolling-Baseline Triggers and Terminal Refusal](134-cost-runaway-ceiling.md) | ✓ accepted | live |
| [ADR-138: NPC Ratification Gates Projection Eligibility — Unratified Pool Members Stay Out of the ADR-118 Index and the ADR-135 Public Surface](138-npc-ratification-gates-projection.md) | ◇ proposed | deferred → Design-only (story 75-9). Governs existing sidequest-server/sidequest/game/npc_pool.py (NpcPoolMember.observation_pending — Story 49-6 gate) and the ADR-118 §D3 NPC to_card() projector (game/entity_card.py / entity_sync.py). Implementation deferred to follow-on stories 75-11..75-14. |

## Game Systems

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-014: Diamonds and Coal](014-diamonds-and-coal.md) | ✓ accepted | — |
| [ADR-015: Character Builder State Machine](015-character-builder-state-machine.md) | ✓ accepted | live |
| [ADR-016: Three-Mode Character Creation](016-three-mode-chargen.md) | ✓ accepted | live |
| [ADR-018: Trope Engine](018-trope-engine.md) | ✓ accepted | live → sidequest-server/sidequest/game/trope_tick.py + trope_time_skip.py — all four pillars wired at _execute_narration_turn (per ADR body 'Remaining gaps: None') |
| [ADR-020: NPC Disposition System](020-npc-disposition-system.md) | ✓ accepted | live |
| [ADR-021: Progression System](021-progression-system.md) | ✓ accepted | *partial* → Track 4 (journey recap) live; tracks 1-3 data-model only, no engine — sprint story 82-3 (milestone level-up TODO progression.py, AffinityState P6-deferred, item narrative_weight P2-deferred) |
| [ADR-022: WorldBuilder Maturity](022-world-builder-maturity.md) | ✓ accepted | live |
| [ADR-023: Session Persistence](023-session-persistence.md) | ✓ accepted | live |
| [ADR-024: Dual-Track Tension Model](024-dual-track-tension-model.md) | ✓ accepted | live |
| [ADR-025: Pacing Detection](025-pacing-detection.md) | ✓ accepted | live |
| [ADR-074: Dice Resolution Protocol — Player-Facing Rolls via WebSocket](074-dice-resolution-protocol.md) | ✓ accepted | live |
| [ADR-077: Dogfight Subsystem via StructuredEncounter Extension](077-dogfight-subsystem.md) | ✓ accepted | live |
| [ADR-080: Unified Narrative Weight Trait](080-unified-narrative-weight-trait.md) | ✓ accepted | — |
| [ADR-081: Advancement Effect Variant Expansion (v1)](081-advancement-effect-variant-expansion.md) | ✓ accepted | deferred → ADR-087 |
| [ADR-096: Cavern Renderer Revival — Pre-Rendered Cellular Caverns for Tactical Maps](096-cavern-renderer-revival.md) | ✓ accepted | live → sidequest-server/sidequest/dungeon/materializer.py (runtime gen, mask_sha OTEL) + sidequest-ui TacticalGridRenderer.tsx (image-mode) |
| [ADR-097: Class Mechanical Surface — One Signature Ability Per Non-Magical Class](097-class-mechanical-surface.md) | ✓ accepted | live |
| [ADR-106: Runtime Procedural Jaquaysed Megadungeon — Contiguous Edge-Expansion, maze-maker Family Port + Complication Ledger](106-runtime-procedural-jaquaysed-megadungeon.md) | ✓ accepted | *partial* → docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md |
| [ADR-109: Persistent Location Descriptions + Mechanical Manifest](109-persistent-location-descriptions-mechanical-manifest.md) | ✓ accepted | live → sidequest-server location two-mode resolver + PgPromotionStore + LOCATION_DESCRIPTION msg + sidequest-ui LocationPanel.tsx (54-1..54-9, 55-1) |
| [ADR-114: Ablative HP Substrate — HP Reclaims the Lethality Track Beneath the Dials](114-ablative-hp-substrate.md) | ✓ accepted | *partial* → docs/superpowers/plans/completed/2026-05-25-swn-hp-substrate.md |
| [ADR-116: A Confrontation Requires an Other — Participant Membership Invariant, Single Opponent-Seater, End-on-No-Other](116-confrontation-requires-an-other.md) | ✓ accepted | *partial* → sprint/context/context-story-59-13.md |
| [ADR-117: Pluggable Ruleset Module System — Per-Genre Resolution Behind a RulesetModule Seam](117-pluggable-ruleset-module-system.md) | ✓ accepted | live → sidequest-server/sidequest/game/ruleset/registry.py — native, swn, cwn, wwn, awn modules live and pack-bound |
| [ADR-125: Chassis/Rig as a First-Class Entity — Bidirectional Bond Ledger, Seven-Tier Threshold Ladder, and Interior Render](125-chassis-rig-entity.md) | ✓ accepted | live |
| [ADR-126: Pluggable Magic System — MagicPlugin Protocol, Import-Time Registry, and Validator Severity Model](126-pluggable-magic-system.md) | ✓ accepted | live |
| [ADR-128: Trope Temporal Governor, Seed-Trope Deck, and NPC Development Ladder — Pile-Up Prevention and Resume-Safe Randomness](128-trope-governor-seed-deck.md) | ✓ accepted | live |
| [ADR-129: N-Seat Table Engine — Generalized Sealed-Commit Loop for Poker/Auction with Cheat/Accuse Mechanics](129-table-game-engine.md) | ✓ accepted | live |
| [ADR-130: Orbital Story-Time Clock and Course Model — Beat-Driven Time Advance and Approximate Hohmann Transit](130-orbital-clock-course.md) | ✓ accepted | live |
| [ADR-136: Player-Facing Relationship Surface — Reactive RELATIONSHIPS Projection, Disposition Beat-Log, and the Claims-Only Belief Firewall](136-player-facing-relationship-surface.md) | ✓ accepted | live → docs/superpowers/plans/2026-06-01-npc-relationship-panel.md |
| [ADR-137: Quest & Stakes Substrate — Create/Anchor Lane, First-Class active_stakes Source, and One-Mechanism Consolidation](137-quest-stakes-substrate.md) | ◇ proposed | *partial* → sidequest-server/sidequest/game/quest_seed.py (story 77-1 seed-at-creation live, quest.seeded_at_creation OTEL); 77-2..77-7 deferred |
| [ADR-139: Confrontation Integrity Invariants — Win-Condition Liveness, Seated-Actor HP Durability, the Mechanically-Capable Other, and the Dispatch Applicability Gate](139-confrontation-integrity-invariants.md) | ✓ accepted | *partial* → sidequest-server/sidequest/game/ — confrontation resolution + ADR-059 monster_manual injection + opponent-seater; first impl on FIXER branches fix/eh-opp-damage and fix/eh-magic-gate (2026-06-04 burning_peace playtest); verification home = Epic 73 Confrontation Engine Hardening |
| [ADR-141: Two-Scale Spatial Model — Galactic Graph (cartography) as Campaign View, Per-System Orrery as Local View; One File Per System](141-two-scale-spatial-model-galactic-graph-and-system-orrery.md) | ✓ accepted | deferred → NOT YET BUILT. Target seams: sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/{cartography.yaml, systems/<system>.yaml} (delete monolithic orbits.yaml fake root); sidequest-server/sidequest/orbital/{course.py scope selection, models.py loader}; sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx (cluster-graph default + orrery drill-down, retire the orbital:boolean whole-Map toggle). |
| [ADR-142: Without Number Core Extraction — an Honest WithoutNumberRulesetModule Base, Reparented WN Siblings, and a Shaped-Attribute Retune](142-without-number-core-extraction.md) | ✓ accepted | *partial* → sidequest-server/sidequest/game/ruleset/without_number.py (extracted WN core); swn/wwn/cwn/awn.py reparented onto it; spans/wn.py slug-parameterized emitters; tests/game/ruleset/test_142_wn_core_extraction.py + test_102_4_wn_turn_model_family.py (shipped #841). Step-2 attributes via RulesConfig.standard_array (content packs). Deferred: lethality tuning (awaits playtest), attribute arrange-path, and the ruleset chargen seam (ADR-143 follow-on). |
| [ADR-143: A Without-Number Binding Replaces the Native Combat Engine — We Bind the Ruleset to Stop Balancing, Not to Balance Against It](143-wn-binding-replaces-native-combat-no-balancing.md) | ✓ accepted | *partial* → sidequest-server/sidequest/server/dispatch/wn_round.py — sealed initiative-round engine; live for WWN hp_depletion combat, residual native-beat reuse + content beat_selection scaffolding to be removed |

## Frontend / Protocol

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-026: Client-Side State Mirror](026-client-state-mirror.md) | ✓ accepted | live |
| [ADR-027: Reactive State Messaging](027-reactive-state-messaging.md) | ✓ accepted | live |
| [ADR-075: 3D Dice Rendering — Three.js + Rapier Physics Overlay](075-3d-dice-rendering.md) | ✓ accepted | *partial* → ADR-087 |
| [ADR-079: Genre Theme System Unification](079-genre-theme-unification.md) | ✓ accepted | live |
| [ADR-094: Orrery Label Placement — Three-Strategy Taxonomy](094-orrery-label-placement-strategies.md) | ✓ accepted | live |
| [ADR-107: Out-of-Band Aside Channel — Non-Turn-Consuming Player→GM Table-Talk](107-out-of-band-aside-channel.md) | ✓ accepted | live → docs/superpowers/specs/2026-05-17-aside-channel-design.md |
| [ADR-133: Client State Reconciliation v2 — Full-Replay Mirror, Streaming-Narration Accumulator, and ImageBus Scrapbook Merge](133-client-state-reconciliation-v2.md) | ✓ accepted | live |

## Multiplayer

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-036: Multiplayer Turn Coordination](036-multiplayer-turn-coordination.md) | ✓ accepted | live |
| [ADR-037: Shared-World / Per-Player State Split](037-shared-world-per-player-state.md) | ✓ accepted | live |
| [ADR-104: Perception Filtering at the Tool Layer](104-perception-filtering-at-the-tool-layer.md) | ✓ accepted | *partial* → ADR-105 |
| [ADR-105: Broadcast-Layer Perception Firewall — Completing ADR-104 in the MP Fan-Out](105-broadcast-layer-perception-firewall.md) | ✓ accepted | live → sidequest-server/sidequest/server/websocket_session_handler.py (NARRATION_SEGMENT fan-out) + visibility_classifier.py — both tracks landed (2026-05-28 amendment) |
| [ADR-108: MP Item Attribution — Per-Recipient Tagging in the Narration Tool Contract](108-mp-item-attribution-recipient-tagging.md) | ✓ accepted | live |
| [ADR-119: Authenticated Player Identity — Player-vs-Character Identity Split via Cloudflare Access](119-authenticated-player-identity.md) | ✓ accepted | *partial* → docs/superpowers/specs/2026-05-31-67-6-player-identity-design.md |
| [ADR-122: SessionRoom Lifecycle — RoomRegistry Never-Evict Policy, LobbyState FSM, Multi-Socket Presence Ref-Counting](122-session-room-lifecycle.md) | ✓ accepted | live |

## Transport / Infrastructure

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-035: Unix Socket IPC for Python Sidecar](035-unix-socket-ipc-sidecar.md) | ✓ accepted | live |
| [ADR-038: WebSocket Transport Architecture](038-websocket-transport-architecture.md) | ✓ accepted | live |
| [ADR-046: GPU Memory Budget Coordinator](046-gpu-memory-budget-coordinator.md) | ✓ accepted | — |
| [ADR-047: Prompt Injection Sanitization Layer](047-prompt-injection-sanitization.md) | ✓ accepted | live |
| [ADR-131: Daemon↔Server Out-of-Band Contracts — Liveness Heartbeat, OTEL HTTP Bridge, Output-Dir Handshake, R2 Artifact Layout](131-daemon-server-oob-contracts.md) | ✓ accepted | live |

## Narrator / Text

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-040: Narrative Character Sheet (No Raw Stats)](040-narrative-character-sheet.md) | ✗ deprecated | — |
| [ADR-049: Narrator Verbosity and Vocabulary (Two-Axis Text Tuning)](049-narrator-verbosity-vocabulary.md) | ✓ accepted | *partial* → Prompt sections fire (orchestrator) but no UI sliders + TurnContext hardcodes defaults — sprint story 82-2 (no production consumer of player verbosity/vocabulary choice) |
| [ADR-052: Narrative Axis System (/tone Command)](052-narrative-axis-system.md) | ✗ deprecated | — |
| [ADR-057: Narrator Crunch Separation — LLM Narrates, Scripts Crunch](057-narrator-crunch-separation.md) | ✗ deprecated | — |

## NPC / Character Systems

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-041: Genie Wish / Consequence Engine](041-genie-wish-consequence-engine.md) | ✓ accepted | **drift** → ADR-087 |
| [ADR-042: OCEAN Personality Live Evolution](042-ocean-personality-live-evolution.md) | ✓ accepted | **drift** → ADR-087 |
| [ADR-053: Scenario System (Clue Graph, Belief State, Gossip Propagation)](053-scenario-system.md) | ✓ accepted | *partial* → ADR-087 |
| [ADR-091: Culture-Corpus + Markov Naming](091-culture-corpus-markov-naming.md) | ✓ accepted | live |

## Media / Audio / Rendering

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-045: Client Audio Engine](045-client-audio-engine.md) | ✓ accepted | live |
| [ADR-048: Lore RAG Store with Cross-Process Embedding](048-lore-rag-store.md) | ✓ accepted | live |
| [ADR-050: Image Pacing Throttle](050-image-pacing-throttle.md) | ✓ accepted | live |
| [ADR-070: MLX Image Renderer — Replace PyTorch/diffusers with Apple MLX](070-mlx-image-renderer.md) | ✓ accepted | live |
| [ADR-086: Image-Composition Taxonomy — Portraits, POIs, Illustrations](086-image-composition-taxonomy.md) | ✓ accepted | live |
| [ADR-095: Daemon Music Tier via ACE-Step](095-daemon-music-tier-via-ace-step.md) | ✓ accepted | live |
| [ADR-127: Image Prompt-Composition Pipeline — Catalog Recipes, Token-Budget Eviction Ladder, and SceneInterpreter Rule Cascade](127-image-composition-pipeline.md) | ✓ accepted | live |

## Turn Management

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-051: Two-Tier Turn Counter (Interaction vs. Round)](051-two-tier-turn-counter.md) | ✓ accepted | live |

## Room Graph / Dungeon Crawl

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-055: Room Graph Navigation](055-room-graph-navigation.md) | ✓ accepted | *partial* → ADR-087 |

## Code Generation / Tooling

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-059: Monster Manual — Server-Side Pre-Generation via Game-State Injection](059-monster-manual-server-side-pregen.md) | ✓ accepted | live |
| [ADR-092: Scene Harness — Dev-Gated HTTP Endpoint for Scenario Fixtures](092-scene-harness-http-endpoint.md) | ✓ accepted | *partial* → ADR-087 |

## Observability

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-090: OTEL Dashboard Restoration after Python Port](090-otel-dashboard-restoration.md) | ✓ accepted | live |
| [ADR-103: Native OTEL via Tool Registry](103-native-otel-via-tool-registry.md) | ✓ accepted | *partial* → ADR-101 |
| [ADR-124: Save-Forensics Architecture — Read-Only Tiered Save Inspection, Loud-Skip Folds, and Per-Round Mechanical Census](124-save-forensics-architecture.md) | ✓ accepted | live |
| [ADR-132: WatcherHub Infrastructure — builtins-Pinned Singleton, ContextVar Per-Session Isolation, and Ephemeral-Event Taxonomy](132-watcherhub-infrastructure.md) | ✓ accepted | live |

## Codebase Decomposition

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-060: Genre Models Decomposition — Split models.rs by Domain](060-genre-models-decomposition.md) | ✓ accepted | live |
| [ADR-061: Lore Module Decomposition — Split lore.rs by Responsibility](061-lore-module-decomposition.md) | ✓ accepted | live |
| [ADR-062: Server lib.rs Extraction — Route Groups, State, and Watcher Events](062-server-lib-extraction.md) | ✓ accepted | live |
| [ADR-063: Dispatch Handler Splitting — By Pipeline Stage](063-dispatch-handler-splitting.md) | ✓ accepted | live |
| [ADR-064: Game Crate Domain Modules — Organize 69 Flat Files](064-game-crate-domain-modules.md) | ✓ accepted | live |
| [ADR-065: Protocol Message Decomposition — Split message.rs by Domain](065-protocol-message-decomposition.md) | ✓ accepted | deferred |
| [ADR-068: Magic Literal Extraction — Domain-Scoped Constants](068-magic-literal-extraction.md) | ✓ accepted | live |
| [ADR-088: ADR Frontmatter Schema and Auto-Generated Indexes](088-adr-frontmatter-schema.md) | ✓ accepted | live |

## Narrator Architecture

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-073: Local Fine-Tuned Model Architecture](073-local-fine-tuned-model-architecture.md) | ✓ accepted | live → ADR-101 |
| [ADR-076: Narration Protocol Collapse Post-TTS Removal](076-narration-protocol-collapse-post-tts.md) | ✓ accepted | live |

## Genre Mechanics

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-031: Game Watcher — Semantic Telemetry for AI Agent Observability](031-game-watcher-semantic-telemetry.md) | ✓ accepted | live |
| [ADR-033: Genre Mechanics Engine — Confrontations & Resource Pools](033-confrontation-engine-resource-pools.md) | ✓ accepted | *partial* → ADR-087 |
| [ADR-093: Confrontation Difficulty Calibration v1](093-confrontation-difficulty-calibration.md) | ✓ accepted | live |
| [ADR-099: Coyote Object Salvage Hooks — Two-Phase Auto-Fire for the_salvage](099-coyote-object-salvage-hooks.md) | ✓ accepted | deferred |

## Project Lifecycle / Meta

| ADR | Status | Impl |
|-----|--------|------|
| [ADR-082: Port `sidequest-api` from Rust back to Python](082-port-api-rust-to-python.md) | ✓ accepted | live |
| [ADR-085: Tracker hygiene during the Rust→Python port — handling port-drift](085-rust-to-python-port-drift.md) | ✓ accepted | live |
| [ADR-087: Post-Port Subsystem Restoration Plan](087-post-port-subsystem-restoration-plan.md) | ✓ accepted | live |

## Superseded / Historical

Retired ADRs. See [SUPERSEDED.md](SUPERSEDED.md) for the grouped view.

| ADR | Status | Successor |
|-----|--------|-----------|
| [ADR-001: Claude CLI Only](001-claude-cli-only.md) | ✗ superseded | [ADR-101](101-anthropic-sdk-as-narrator-backend.md) |
| [ADR-010: Intent-Based Agent Routing](010-intent-based-agent-routing.md) | ✗ superseded | [ADR-067](067-unified-narrator-agent.md) |
| [ADR-017: Cinematic Chase Engine](017-cinematic-chase-engine.md) | ✗ superseded | [ADR-033](033-confrontation-engine-resource-pools.md) |
| [ADR-019: Cartography Discovery](019-cartography-discovery.md) | ✗ superseded | [ADR-082](082-port-api-rust-to-python.md) |
| [ADR-028: Perception Rewriter](028-perception-rewriter.md) | ✗ superseded | [ADR-104](104-perception-filtering-at-the-tool-layer.md) |
| [ADR-029: Guest NPC Players](029-guest-npc-players.md) | ✗ historical | — |
| [ADR-030: Scenario Packs](030-scenario-packs.md) | ✗ superseded | [ADR-053](053-scenario-system.md) |
| [ADR-032: Genre-Specific LoRA Style Training for Flux Image Generation](032-genre-lora-style-training.md) | ✗ superseded | [ADR-070](070-mlx-image-renderer.md) |
| [ADR-034: Portrait Identity Consistency — Tiered Character Recognition Pipeline](034-portrait-identity-consistency.md) | ✗ superseded | [ADR-086](086-image-composition-taxonomy.md) |
| [ADR-039: Narrator Structured Output (JSON Sidecar Block)](039-narrator-structured-output.md) | ✗ superseded | [ADR-102](102-tool-use-protocol-for-structured-output.md) |
| [ADR-043: Conlang Morpheme System](043-conlang-morpheme-system.md) | ✗ superseded | [ADR-091](091-culture-corpus-markov-naming.md) |
| [ADR-044: Speculative Prerendering During TTS Playback](044-speculative-prerendering.md) | ✗ historical | — |
| [ADR-054: WebRTC Voice Chat (Disabled — Echo Feedback Loop)](054-webrtc-voice-chat-disabled.md) | ✗ historical | — |
| [ADR-056: Script Tool Generators — Offloading Structured Generation from LLM to Rust Binaries](056-script-tool-generators.md) | ✗ superseded | [ADR-059](059-monster-manual-server-side-pregen.md) |
| [ADR-058: Claude Subprocess OTEL Passthrough](058-claude-subprocess-otel-passthrough.md) | ✗ superseded | [ADR-103](103-native-otel-via-tool-registry.md) |
| [ADR-066: Persistent Opus Narrator Sessions](066-persistent-opus-narrator-sessions.md) | ✗ superseded | [ADR-098](098-stateless-narrator-turns.md) |
| [ADR-069: Scenario Fixtures — Pre-configured World States for Testing](069-scenario-fixtures.md) | ✗ superseded | [ADR-092](092-scene-harness-http-endpoint.md) |
| [ADR-071: Tactical ASCII Grid Maps — Deterministic Room Layout via ASCII Art](071-tactical-ascii-grid-maps.md) | ✗ superseded | [ADR-086](086-image-composition-taxonomy.md) |
| [ADR-072: System/Milieu Decomposition — Separating Mechanics from Aesthetic](072-system-milieu-decomposition.md) | ✗ historical | — |
| [ADR-078: Edge / Composure Combat, Mechanical Advancement, and Push-Currency Rituals](078-edge-composure-advancement-rituals.md) | ✗ superseded | [ADR-114](114-ablative-hp-substrate.md) |
| [ADR-083: Multi-LoRA Stacking and Verification Pipeline](083-multi-lora-stacking-and-verification.md) | ✗ historical | — |
| [ADR-084: Compositional-Dimension Specialization for Style LoRAs](084-lora-composition-dimension.md) | ✗ superseded | [ADR-070](070-mlx-image-renderer.md) |
| [ADR-089: Pre-Rendered Cavern Battle Maps via Ported Cellular Automata](089-cavern-template-generation.md) | ✗ superseded | [ADR-096](096-cavern-renderer-revival.md) |
| [ADR-120: Genre/World Flavor Boundary — Mandatory-File Loader Contract, Mechanics-in-Genre, Flavor-in-World](120-genre-world-flavor-boundary.md) | ✗ superseded | [ADR-140](140-genre-rulebook-world-cast-catalog.md) |

## Implementation Drift

ADRs whose implementation is absent, partial, or deferred. See [DRIFT.md](DRIFT.md) for priority-tier details.

| ADR | Impl | Pointer |
|-----|------|---------|
| [ADR-065: Protocol Message Decomposition — Split message.rs by Domain](065-protocol-message-decomposition.md) | deferred | — |
| [ADR-081: Advancement Effect Variant Expansion (v1)](081-advancement-effect-variant-expansion.md) | deferred | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-099: Coyote Object Salvage Hooks — Two-Phase Auto-Fire for the_salvage](099-coyote-object-salvage-hooks.md) | deferred | — |
| [ADR-138: NPC Ratification Gates Projection Eligibility — Unratified Pool Members Stay Out of the ADR-118 Index and the ADR-135 Public Surface](138-npc-ratification-gates-projection.md) | deferred | Design-only (story 75-9). Governs existing sidequest-server/sidequest/game/npc_pool.py (NpcPoolMember.observation_pending — Story 49-6 gate) and the ADR-118 §D3 NPC to_card() projector (game/entity_card.py / entity_sync.py). Implementation deferred to follow-on stories 75-11..75-14. |
| [ADR-141: Two-Scale Spatial Model — Galactic Graph (cartography) as Campaign View, Per-System Orrery as Local View; One File Per System](141-two-scale-spatial-model-galactic-graph-and-system-orrery.md) | deferred | NOT YET BUILT. Target seams: sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/{cartography.yaml, systems/<system>.yaml} (delete monolithic orbits.yaml fake root); sidequest-server/sidequest/orbital/{course.py scope selection, models.py loader}; sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx (cluster-graph default + orrery drill-down, retire the orbital:boolean whole-Map toggle). |
| [ADR-013: Lazy JSON Extraction](013-lazy-json-extraction.md) | **drift** | [ADR-102](102-tool-use-protocol-for-structured-output.md) |
| [ADR-041: Genie Wish / Consequence Engine](041-genie-wish-consequence-engine.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-042: OCEAN Personality Live Evolution](042-ocean-personality-live-evolution.md) | **drift** | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-021: Progression System](021-progression-system.md) | *partial* | Track 4 (journey recap) live; tracks 1-3 data-model only, no engine — sprint story 82-3 (milestone level-up TODO progression.py, AffinityState P6-deferred, item narrative_weight P2-deferred) |
| [ADR-033: Genre Mechanics Engine — Confrontations & Resource Pools](033-confrontation-engine-resource-pools.md) | *partial* | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-049: Narrator Verbosity and Vocabulary (Two-Axis Text Tuning)](049-narrator-verbosity-vocabulary.md) | *partial* | Prompt sections fire (orchestrator) but no UI sliders + TurnContext hardcodes defaults — sprint story 82-2 (no production consumer of player verbosity/vocabulary choice) |
| [ADR-053: Scenario System (Clue Graph, Belief State, Gossip Propagation)](053-scenario-system.md) | *partial* | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-055: Room Graph Navigation](055-room-graph-navigation.md) | *partial* | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-075: 3D Dice Rendering — Three.js + Rapier Physics Overlay](075-3d-dice-rendering.md) | *partial* | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-092: Scene Harness — Dev-Gated HTTP Endpoint for Scenario Fixtures](092-scene-harness-http-endpoint.md) | *partial* | [ADR-087](087-post-port-subsystem-restoration-plan.md) |
| [ADR-101: Anthropic SDK as Narrator Backend](101-anthropic-sdk-as-narrator-backend.md) | *partial* | Backend live + default on develop: sidequest-server/sidequest/agents/llm_factory.py (default anthropic_sdk), anthropic_sdk_client.py, model_routing.py, anthropic_cost.py. Phased cleanups (sidecar/perception-rewriter/OTEL-scraper deletion) tracked by ADR-102/104/103. |
| [ADR-102: Tool-Use Protocol for Structured Output](102-tool-use-protocol-for-structured-output.md) | *partial* | [ADR-101](101-anthropic-sdk-as-narrator-backend.md) |
| [ADR-103: Native OTEL via Tool Registry](103-native-otel-via-tool-registry.md) | *partial* | [ADR-101](101-anthropic-sdk-as-narrator-backend.md) |
| [ADR-104: Perception Filtering at the Tool Layer](104-perception-filtering-at-the-tool-layer.md) | *partial* | [ADR-105](105-broadcast-layer-perception-firewall.md) |
| [ADR-106: Runtime Procedural Jaquaysed Megadungeon — Contiguous Edge-Expansion, maze-maker Family Port + Complication Ledger](106-runtime-procedural-jaquaysed-megadungeon.md) | *partial* | docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md |
| [ADR-110: Game-State Snapshot Slimming — Compact Encoding + Allowlist Pruning, Diff-with-Anchor Deferred](110-game-state-snapshot-slimming.md) | *partial* | sidequest-server/sidequest/server/session_helpers.py#_PHASE_B_DROP_FIELDS |
| [ADR-112: Genre Prose Cache Promotion — Four Always-Fire Session-Static Sections Move to Stable, Conditional Sections Defer](112-genre-prose-stable-cache-promotion.md) | *partial* | sprint/current-sprint.yaml#57-3 |
| [ADR-114: Ablative HP Substrate — HP Reclaims the Lethality Track Beneath the Dials](114-ablative-hp-substrate.md) | *partial* | docs/superpowers/plans/completed/2026-05-25-swn-hp-substrate.md |
| [ADR-116: A Confrontation Requires an Other — Participant Membership Invariant, Single Opponent-Seater, End-on-No-Other](116-confrontation-requires-an-other.md) | *partial* | sprint/context/context-story-59-13.md |
| [ADR-119: Authenticated Player Identity — Player-vs-Character Identity Split via Cloudflare Access](119-authenticated-player-identity.md) | *partial* | docs/superpowers/specs/2026-05-31-67-6-player-identity-design.md |
| [ADR-135: Reference Pages Are a Public Table Tool — Single Fixed Projection, No GM Audience](135-reference-pages-public-table-tool.md) | *partial* | sidequest-server reference_renderer.py — audience doctrine + stories 65-7..65-9 live; 65-10..65-12 pending. The 2026-06-08 amendment (server-projection / React-render seam) reframes the render substrate from server HTML to a projected JSON API + React SPA — design-only, implementation tracked as epic 100; see the Amendment section and docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md. |
| [ADR-137: Quest & Stakes Substrate — Create/Anchor Lane, First-Class active_stakes Source, and One-Mechanism Consolidation](137-quest-stakes-substrate.md) | *partial* | sidequest-server/sidequest/game/quest_seed.py (story 77-1 seed-at-creation live, quest.seeded_at_creation OTEL); 77-2..77-7 deferred |
| [ADR-139: Confrontation Integrity Invariants — Win-Condition Liveness, Seated-Actor HP Durability, the Mechanically-Capable Other, and the Dispatch Applicability Gate](139-confrontation-integrity-invariants.md) | *partial* | sidequest-server/sidequest/game/ — confrontation resolution + ADR-059 monster_manual injection + opponent-seater; first impl on FIXER branches fix/eh-opp-damage and fix/eh-magic-gate (2026-06-04 burning_peace playtest); verification home = Epic 73 Confrontation Engine Hardening |
| [ADR-140: Genre Is the Rulebook Only; the World Owns the Cast and Catalog — Supersedes ADR-120's Mechanics-in-Genre](140-genre-rulebook-world-cast-catalog.md) | *partial* | sidequest-server/sidequest/genre/loader.py (_load_single_world world-tier classes/spells_wwn/seed_tropes loads + pack-level world-first aggregation), sidequest/server/dispatch/{class_resolve,char_creation_resolve,wwn_spell_catalog_resolve}.py (world-first resolvers), sidequest/genre/models/pack.py (World.classes / World.wwn_spell_catalog / World.chassis_classes / World.seed_tropes). Delivered by epic 94 stories 94-1..94-3. |
| [ADR-142: Without Number Core Extraction — an Honest WithoutNumberRulesetModule Base, Reparented WN Siblings, and a Shaped-Attribute Retune](142-without-number-core-extraction.md) | *partial* | sidequest-server/sidequest/game/ruleset/without_number.py (extracted WN core); swn/wwn/cwn/awn.py reparented onto it; spans/wn.py slug-parameterized emitters; tests/game/ruleset/test_142_wn_core_extraction.py + test_102_4_wn_turn_model_family.py (shipped #841). Step-2 attributes via RulesConfig.standard_array (content packs). Deferred: lethality tuning (awaits playtest), attribute arrange-path, and the ruleset chargen seam (ADR-143 follow-on). |
| [ADR-143: A Without-Number Binding Replaces the Native Combat Engine — We Bind the Ruleset to Stop Balancing, Not to Balance Against It](143-wn-binding-replaces-native-combat-no-balancing.md) | *partial* | sidequest-server/sidequest/server/dispatch/wn_round.py — sealed initiative-round engine; live for WWN hp_depletion combat, residual native-beat reuse + content beat_selection scaffolding to be removed |

<!-- ADR-INDEX:GENERATED:END -->
