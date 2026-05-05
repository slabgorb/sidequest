# SideQuest Feature Inventory

**Last updated:** 2026-05-05
**Sprint 3:** Playtest 3 closeout — MP correctness, state hygiene, post-port cleanup (active 2026-04-27 → 2026-05-10)
**Sprint 3 progress:** 49/60 stories done · 135/168 points · 11 in backlog
**Sprint 3 epics:** Epic 45 (single-epic absorber for Epic 37 backlog + port-drift residue) and Epic 47 (Magic system + Rig MVP)

> **Post-port snapshot.** This inventory describes the **Python** backend
> (`sidequest-server`) live since the ADR-082 cutover (2026-04-23). The
> language-level Rust → Python port is complete; subsystem-level drift is
> tracked separately. For the comprehensive non-parity inventory and
> verdicts, see:
>
> - `docs/port-drift-feature-audit-2026-04-24.md` — what landed in Python and what didn't
> - `docs/adr/087-post-port-subsystem-restoration-plan.md` — verdict + tier per non-parity subsystem (last sweep 2026-05-02)
> - `docs/adr/README.md` — port-era reading guide and Rust → Python translation table

## Legend

- **Live & Wired** — Implemented in Python, reachable from real session traffic, OTEL-emitting
- **Live (partial)** — Wired but not fully exercised, or has a known gap flagged by ADR-087
- **Dark** — Concept ported to Python data model only; engine missing (per ADR-087 RESTORE roster)
- **Deferred** — Intentional phased scope; marker present or covered by Proposed ADR
- **Workshop only** — Genre content lives in `sidequest-content/genre_workshopping/` and is not selectable in the UI

**Wiring diagrams:** See [`docs/wiring-diagrams.md`](wiring-diagrams.md) for end-to-end signal traces (Mermaid) showing each feature's path from UI to storage.

---

## Live & Wired (Post-Port)

These features are wired end-to-end in the Python tree and exercise OTEL spans during real sessions.

### Core Game Loop

| Feature | Server module | UI | Notes |
|---------|---------------|----|-------|
| WebSocket transport | `sidequest.server.websocket` + `websocket_session_handler` | `useGameSocket` / `useWebSocket` | FastAPI WS upgrade, reader/writer task split (ADR-038) |
| REST genres endpoint | `sidequest.server.rest` + `views` | `ConnectScreen` | `/api/genres` — pack discovery |
| Session lifecycle | `sidequest.server.session_handler` + `session_helpers` | `ConnectScreen → GameLayout` | Connect → Create → Play, pydantic-validated |
| Multiplayer rooms | `sidequest.server.session_room` | shared-world state | `SessionRoom` keyed by `genre:world` (ADR-036/037) |
| Connect handshake | `sidequest.handlers.connect` | `ConnectScreen` | New typed handler; replaced inline session_handler logic |
| Character creation | `sidequest.game.builder` + `character` + `archetype_apply` | `CharacterCreation` | Genre-driven scene state machine, three modes (ADR-016) |
| Chargen dispatch | `server.dispatch.char_creation_resolve` + `chargen_loadout` + `chargen_summary` | — | Dispatch package split out of session_handler (ADR-063 partly executed) |
| Orchestrator turn loop | `sidequest.agents.orchestrator` | `NarrativeView` / `NarrationCards` | Intent → Narrator → Patches → Broadcast |
| Intent classification | `sidequest.agents.orchestrator` (state-override) | — | `in_combat`/`in_chase`/default; no LLM call (ADR-067) |
| Unified narrator | `sidequest.agents.narrator` + `claude_client` + `claude_stream_parser` + `stream_fence` | — | Single persistent Opus session via `claude -p` (ADR-067 supersedes multi-agent ADR-010) |
| Narrator session crash recovery | `sidequest.agents.narrator` (warm reboot path) | — | Reactive recovery wired (story 45-50, ADR-066 §8); proactive watchdog still backlog (45-51) |
| Auxiliary subsystem agents | `sidequest.agents.subsystems/` (chassis_voice, distinctive_detail, npc_agency, reflect_absence) | — | Topologically-sorted dispatch off the live turn critical path |
| Sidecar tool patches | `agents.orchestrator.assemble_turn` | — | Narrator emits prose; sidecar tools write JSONL for items/mood/intent/SFX (ADR-039) |
| Encounter render helper | `agents.encounter_render` | — | Python-era helper; renders encounter context for narrator |
| State delta computation | `sidequest.game.delta` (`compute_delta`) | `useStateMirror` | Wire-efficient state diff per turn |
| Projection package | `sidequest.game.projection/` (`cache`, `cache_fill`, `composed`, `envelope`, `field_path`, `genre_stage`, `invariants`, `predicates`, `rules`, `validator`, `view`) + top-level `projection_filter.py` | per-client `INITIAL_STATE`/deltas | Decomposed projection-filter; OTEL `projection_decide_span`; predicate validators ensure invariants |
| Narration delivery | `sidequest.protocol.messages.NARRATION` + `NARRATION_END` + `THINKING` | `NarrativeView`, `NarrationCards`, `NarrationFocus`, `NarrationScroll` (markdown, DOMPurify) | Two-message atomic state commit (ADR-076 retired streaming chunks) |
| SQLite persistence | `sidequest.game.persistence` + `migrations` | — | `sqlite3` via `asyncio.to_thread`; one DB per save; schema migrations honored |
| Genre pack loading | `sidequest.genre.loader` + `models/` + `resolver` + `cache` + `genre_code` | `ThemeProvider` | YAML → pydantic; lazy bind on connect (ADR-004); pointer resolution + subdirectory cascade |
| Lethality policy loader | `sidequest.genre.lethality_policy_loader` | — | Per-genre lethality policy YAML loaded into resolver |
| Magic loader | `sidequest.genre.magic_loader` | — | Loads `magic.yaml` + plugin registry into world config |
| CORS | FastAPI middleware | Vite proxy | Dev + prod |
| Production tunnel | `just serve` + `just tunnel` recipes | — | Cloudflare tunnel for prod; per-player `*.local` host entries (see project memory) |

### Multiplayer & Pacing

| Feature | Module | Notes |
|---------|--------|-------|
| Turn barrier (sealed-letter window) | `sidequest.server.session_room.TurnBarrier` | Adaptive timeout (3s for 2-3, 5s for 4+); claim-election prevents duplicate narrator calls |
| Active-turn-takers vs lobby count | story 45-2 | Closed Sprint 3; barrier no longer waits on phantom lobby peers |
| Shared-world delta handshake | `sidequest.game.shared_world_delta` | Closed Sprint 3 (story 45-1); seeds next player's turn with location/encounter/adjacency ground truth |
| Sealed-letter dispatch | `sidequest.server.dispatch.sealed_letter` | Phase-5 dispatch handler restored (used by dogfight `ResolutionMode.sealed_letter_lookup` and magic confrontation outcomes) |
| Three turn modes | `sidequest.game.session.TurnMode` | FREE_PLAY, STRUCTURED, CINEMATIC (ADR-036) |
| Party action composition | `sidequest.agents.orchestrator` | Multi-character PARTY ACTIONS block in narrator prompt |
| Perception rewriter | `sidequest.agents.perception_rewriter` | Per-player narration variants based on status effects (ADR-028) |
| LocalDM dispatch package | `sidequest.agents.local_dm` (DORMANT on live path) + `protocol.dispatch.DispatchPackage` | Per-player visibility/perception/fidelity baseline structure; runtime dormant (LocalDM corpus extraction is offline-only via `corpus.miner` per 2026-04-28 spec) |
| Two-tier turn counter | `sidequest.game.turn` | Interaction (monotonic) vs Round (narrative) — ADR-051 |
| TensionTracker | `sidequest.game.tension_tracker` | Dual-track model — gambler's ramp + Edge stakes + event spikes (HP fields vestigial, story 45-35 removed HP from chargen) |
| Drama-aware delivery | narration_apply consumers | INSTANT / SENTENCE / STREAMING (drama_weight thresholds) |
| Quiet turn detection | `sidequest.game.tension_tracker` | Escalation beat injection after sustained low drama |
| Genre-tunable thresholds | `pacing.yaml` per pack | Per-pack drama breakpoints |
| Momentum readout sync | story 45-3 | UI ConfrontationOverlay reads live momentum off state mirror; `encounter.momentum_broadcast` OTEL span |
| Player presence + seat | `handlers.player_seat` + `protocol.PLAYER_PRESENCE`, `PLAYER_SEAT`, `SEAT_CONFIRMED` | Lobby-state observability; supports paused/abandoned slot detection |
| Game pause/resume | `protocol.GAME_PAUSED`, `GAME_RESUMED` + `PausedBanner` | Server-driven session pause |
| Yield action | `handlers.yield_action` + `server.dispatch.yield_action` + `YieldButton` | Voluntary turn yield; calls `apply_edge_delta` |

### Knowledge & Lore

| Feature | Module | Notes |
|---------|--------|-------|
| KnownFact accumulation | `sidequest.game.character.KnownFact` | Tiered injection by relevance |
| Footnote protocol | `sidequest.protocol.messages.NarrationPayload.footnotes` | Discovery / callback styling, fact_id callbacks |
| Lore store | `sidequest.game.lore_store` | In-memory indexed collection, persisted via SQLite |
| Lore RAG (embedding cosine sim) | `sidequest.game.lore_embedding` (cross-process via daemon, ADR-048) | Ported intact |
| Lore seeding from packs | `sidequest.game.lore_seeding` | Bootstrap from genre/world YAML |
| Lore embedding dispatch | `server.dispatch.lore_embed` | Server-side embedding fan-out per turn |
| Knowledge Journal | `KnowledgeJournal.tsx` | Player-facing journal panel; keyword-filter spec drafted (token AND match), implementation planned |
| Belief state (multi-source credibility) | `sidequest.game.belief_state` | Ported intact |
| Scenario / clue graph | `sidequest.game.scenario_state` | Bottle episodes, whodunit data; scenario_bind dispatch handler |

### NPC & World Systems

| Feature | Module | Notes |
|---------|--------|-------|
| OCEAN profiles (data) | `sidequest.genre.models.ocean` | Five floats 0.0–10.0 on every archetype |
| OCEAN behavioral summary | `OceanProfile.behavioral_summary()` | Scores → prompt text |
| Narrator reads OCEAN | `agents.prompt_framework` | Voice/behavior adjustment per NPC |
| OCEAN shift proposals | — | **Dark** — model present, evolution pipeline not ported (ADR-087 RESTORE P2) |
| Disposition (scalar) | `game.character.npc.disposition` | Reduced to scalar int with clamping; **Attitude enum + transitions are dark** (ADR-087 RESTORE P1) |
| NPC pool / NPC state split | `game.npc_pool` (story 45-47 Wave 2A) | Pool/state decomposition; Wave 2A landed; cleanup (45-52: NpcRegistryEntry drop + observability counters) backlog |
| Faction agendas | `game.faction_agenda` (data ported) + narrator injection | Goals + urgency feed scene directives |
| Authored NPCs | `genre.models.authored_npc` | Pre-authored NPC definitions per pack |
| Scene directives | `agents.prompt_framework` (early-zone) | Mandatory weave |
| Trope ticks (data) | `game.session.TropeState` + `game.trope_tick` + `trope_tuning` | Progression cooldown + simultaneous-active cap (story 45-27); engine that fires beats from progression remains dark (ADR-087 RESTORE P1) |
| World materialization | `game.world_materialization` | Campaign maturity (fresh/early/mid/veteran) |
| Region init / validation | `game.region_init`, `region_validation` | Seed `snap.current_region` from world `cartography.yaml` (ADR-019 supersession residual). Reject non-room entries (45-16); slug normalization at write (45-17) |
| Region state spans | `telemetry.spans.region_state` | OTEL coverage on region transitions |
| Resource pool | `game.resource_pool` | Thresholds + decay; underpins genre-typed resources (humanity, heat, fuel, voice/flesh/ledger pact pools) |
| Resolution signal | `game.resolution_signal` | Handshake plumbing for momentum/beat resolution; underpins story 45-3 |
| Scrapbook coverage | `game.scrapbook_coverage` | Tracks rendered illustrations against narrative beats; backfill detection on save resume (45-10) |
| World history arcs | `game.history_chapter` | Arc embedding writeback to narrative_log/lore (45-23); arcs extend past turn 30 (45-19) |

### Confrontation Engine (ADR-033)

| Feature | Module | Status |
|---------|--------|--------|
| StructuredEncounter / ConfrontationDef / `apply_beat` (Pillar 1) | `game.encounter`, `game.beat_kinds`, `game.opposed_check`, `server.dispatch.confrontation` | **Live** — verified 2026-05-02 |
| ResourcePool + threshold→KnownFact mint (Pillar 2) | `game.resource_pool`, `game.thresholds`, `mint_threshold_lore` | **Live** — verified 2026-05-02 |
| Difficulty calibration v1 (ADR-093) | encounter difficulty math | **Live** — story 45-42; analytical-distribution + ship_combat correction |
| `mood_aliases` alias-chain consumer (Pillar 3) | `genre.models.audio.mood_aliases`, MusicDirector | **Dark (polish)** — field declared, one pack uses it; consumer not wired (ADR-087 P3) |
| `mood_override` step | live | Live — narration-driving step is wired |
| Confrontation outcome dispatch | `protocol.CONFRONTATION_OUTCOME` + `LedgerPanel` | Magic Phase 5 wire message (story 47-3) |
| Encounter lifecycle dispatch | `server.dispatch.encounter_lifecycle` | XP awards (partial stub — `award_turn_xp`); deferred per ADR-081 |

### Combat / Edge / Composure (ADR-078, ADR-014)

| Feature | Module | Status |
|---------|--------|--------|
| Edge primitive on CreatureCore | `game.creature_core.EdgePool`, `apply_edge_delta` | **Live** — wired from `dispatch/yield_action.py:43`, `game/session.py:884,888` |
| Shared threshold helper | `game.thresholds` | **Live** — extracted; covers crossings + threshold→KnownFact mint |
| `BeatDef.edge_delta` field | `genre.models.rules.BeatDef` | **Live** — beat-driven edge mutation wired |
| HP removal | story 45-35 | **Live** — HP fields removed from CreatureCore + chargen; vestigial fields in `tension_tracker.py:340-350` and `history_chapter.py:64` flagged for cleanup |
| Combatant / opposed check | `game.combatant`, `opposed_check`, `combat_brackets` (dispatch) | **Live** — combat brackets dispatch ported |
| Advancement-effect data shapes | `genre.models.advancement` | **Live** — shapes loaded; effect runtime upstream-blocked on Epic 39 (per-class edge config) |
| `composure_break` OTEL span | telemetry/spans/combat | **Dark** — span not emitted; resolution at edge≤0 not yet wired (ADR-078 §4) |
| Push-currency rituals (pact_working) | content in `genre_workshopping/heavy_metal/` | **Workshop only** — production migration pending |
| Per-class edge config wiring | Epic 39 follow-up | **Deferred** — `world_materialization.py:325` placeholder explicit about it |
| Opposed-check / `course_geometry` math | `game.opposed_check`, `orbital.course_geometry` | Live — used by orbital course plotting |

### Magic System (Epic 47)

| Feature | Module | Status |
|---------|--------|--------|
| MagicPlugin protocol | `magic.plugin.MagicPlugin` + `MAGIC_PLUGINS` registry | **Live** — runtime-checkable Protocol; plugins self-register at import |
| Innate v1 plugin | `magic.plugins.innate_v1` (.py + .yaml) | **Live** — coyote_star + heavy_metal references |
| Item-legacy v1 plugin | `magic.plugins.item_legacy_v1` (.py + .yaml) | **Live** |
| MagicState + LedgerBars | `magic.state` (`BarKey`, `LedgerBar`, `MagicState`, `WorkingRecord`, `ApplyWorkingResult`, `ThresholdCrossingEvent`) | **Live** — per-character ledger bars with thresholds |
| Magic context block | `magic.context_builder.build_magic_context_block` | **Live** — narrator prompt injection |
| Magic validator + flags | `magic.validator` + `Flag`/`FlagSeverity`/`HardLimit`/`StatusPromotion` | **Live** — yellow/red/deep_red flag escalation |
| Magic confrontations | `magic.confrontations` | **Live** — five wired confrontations: `the_standoff`, `the_salvage`, `the_bleeding_through`, `the_quiet_word`, `the_long_resident` (story 47-3) |
| Magic-init server hook | `server.magic_init` | **Live** — boots magic state at world load |
| Magic state bars at world-load | initialization in session_handler | **Live (partial)** — initialization story 47-7 backlog (uninit warning span) |
| Tea ritual auto-fire | three-layer fix story 47-6 | **Live** — room matcher, bond rebind, opening hook, OTEL all landed |
| LedgerPanel (UI) | `LedgerPanel.tsx` | **Live** — surfaces magic ledger bars; reacts to `CONFRONTATION_OUTCOME` |
| Magic playtest (multiplayer stabilization) | story 47-5 | **Backlog** |
| Coyote Object salvage hooks | story 47-8 | **Backlog** — design (ADR + scenario seed) |

### Rig System (sibling to Magic, in-progress)

| Feature | Module | Status |
|---------|--------|--------|
| Rig framework decisions | (project memory `project_rig_framework_decisions.md`) | α/R/D3/S2/C3 locked; Coyote Star is flagship |
| Tea brew confrontation | story 47-4 | **Live** — `the_tea_brew` confrontation wired |
| Cliché-judge hook #7 | rig validation hook | Recently activated (chassis name-form vs bond tier) |

### Orbital Chart / Course Plotting (ADR-094)

| Feature | Module | UI | Status |
|---------|--------|----|----|
| Body / orbits config | `orbital.models.BodyDef`, `OrbitsConfig` + `orbital.loader` | — | World-loaded from `worlds/<world>/chart.yaml` |
| Position computation | `orbital.position` + `orbital.clock` | — | Time-driven body positions |
| Course plotting | `orbital.course` + `orbital.course_geometry` (compute_eta_and_dv) | `useOrbitalChart` + `OrbitalChartView` | Player-driven course intent → eta + Δv |
| Course intent dispatch | `handlers.course_intent` + `protocol.course_intent` | `OrbitalChart` HUD | New wire path (ORBITAL_INTENT inbound) |
| Orbital chart render | `orbital.render` + `orbital.course_render` | `OrbitalChart/HudTopStrip`, `HudBottomStrip` | Server SVG renderer; UI overlays HUD strips |
| Conjunction beats | `orbital.conjunction` + `orbital.beats` | — | Astronomical conjunction → narrative beats |
| Label placement | `orbital.label_strategy` (three-strategy taxonomy ADR-094) | label callouts in chart | Story 45-43 + 45-40 (HUD palette aesthetic) |
| Palette | `orbital.palette` | — | Black ground, brass-amber phosphor, white reserved for party marker |
| Display | `orbital.display` + `orbital.intent` | `ORBITAL_CHART` outbound message | SVG-based chart payload |

### Interior / Ship (Kestrel)

| Feature | Module | UI | Status |
|---------|--------|----|----|
| Chassis interior SVG renderer | `interior.render` + `interior.loader` + `interior.dispatch` | `useChassisInteriorSVG` + `GameBoard/widgets/ShipWidget` | 2x2 hardcoded layout for `voidborn_freighter` (the Kestrel); generalizing across chassis classes deferred |
| Chassis classes | `genre.models.chassis` + `chassis_classes.yaml` | — | Genre-pack-defined chassis catalog |
| Chassis voice subsystem | `agents.subsystems.chassis_voice` | — | Voice/personality of the rig itself |
| Chromed archetype | `useChromeArchetype` | character UI | Resolves the player's chromed archetype for display |

### Media Pipeline

| Feature | Module | Notes |
|---------|--------|-------|
| Image generation | `daemon_client` → `sidequest-daemon` (Z-Image MLX, Flux retired) | ADR-070 |
| Daemon pipeline factory | `sidequest_daemon.media.pipeline_factory` + `recipe_loader` + `recipes` | Recipe-driven pipeline assembly |
| Daemon prompt composer | `sidequest_daemon.media.prompt_composer` | Composes per-render prompts from camera specs + recipes |
| Daemon GPU detection | `sidequest_daemon.media.gpu_detect` | Hardware capability probe |
| Daemon post-processor | `sidequest_daemon.media.post_processor` | Post-render image processing |
| Daemon subject extractor | `sidequest_daemon.media.subject_extractor` | Subject extraction (preferred over regex fallback) |
| Daemon Z-Image MLX worker | `sidequest_daemon.media.workers.zimage_mlx_worker` | MLX-native Z-Image worker |
| Daemon Z-Image config | `sidequest_daemon.media.zimage_config` | Tier-driven config; high-fidelity tier story 45-38, worker swap 45-39 |
| Daemon catalogs / camera specs | `sidequest_daemon.media.catalogs` + `camera_specs` | Camera spec catalog |
| Daemon preview | `sidequest_daemon.media.preview` | Quick-render preview |
| Daemon R2 writer | `sidequest_daemon.media.r2_writer` | Cloudflare R2 cloud media writeback |
| LoRA training pipeline | `sidequest_daemon.training.{cli,corpus_loader,format,trainer}` | Daemon-resident LoRA training (ADR-032/083/084 lineage) |
| Render tiers | per `visual_style.yaml` | scene_illustration, portrait, portrait_square, landscape, text_overlay, fog_of_war (cartography retired 2026-04-28; tactical_sketch retired under ADR-086) |
| Image composition taxonomy | (ADR-086) | Portraits, POIs, illustrations canonicalized |
| Subject extraction | narrator `visual_scene` (preferred) + regex fallback | — |
| Image pacing throttle | `sidequest.server.image_pacing` | 30s solo, 60s multiplayer (ADR-050); DM override |
| Render trigger policy | `sidequest.server.render_trigger` + `render_diagnostics` | Story 45-30 — explicit trigger reasons in `render.trigger` OTEL span |
| Render mounts | `sidequest.server.render_mounts` | FastAPI static mounts for render output |
| Asset URLs | `sidequest.server.asset_urls` | Local + R2 asset URL resolution |
| Image silent-fallback teardown | story 45-37 | Killed SF1-SF7 paths; `render.completed` is now a lie detector |
| Render queue with content dedup | daemon pipeline | SHA256 dedup |
| Daemon worker heartbeat | story 45-31 | Render-unavailable degradation |
| Daemon span-context per-call art_style scoping | story 45-29 | Per-call scoping, not global |
| Beat filter (drama gate) | inline in orchestrator + `daemon.renderer.beat_filter` | Daemon-side filter ported; standalone server module dark (ADR-087 P3) |
| Speculative prerender | — | **Do not restore** (ADR-044 historical 2026-05-02 — TTS-deprecated premise) |
| Scene relevance validator | — | **Dark** — REDESIGN under ADR-086 image-composition taxonomy (ADR-087 P2) |
| Music director | `sidequest.audio.{interpreter,library_backend,protocol,rotator}` + `audio.models` | Mood-indexed pre-rendered ACE-Step tracks |
| Daemon audio pipeline | `sidequest_daemon.audio.{interpreter,library_backend,mixer,queue,protocol,rotator}` + `models` | 2-channel mixer (music + SFX); pygame backend |
| Daemon scene interpreter | `sidequest_daemon.scene_interpreter` | Maps narration → audio cues |
| Audio cue messages | `protocol.messages.AUDIO_CUE` + `server.audio_cue` | `useAudioCue` on client; `AudioStatus`, `AudioWidget` panels |
| Client audio engine | `sidequest-ui/src/audio/{AudioEngine,AudioCache,Crossfader}` | Cross-fade transitions; per-channel cache (ADR-045) |
| 2-channel audio | `sidequest-daemon` (pygame mixer) | Music + SFX only (no voice/TTS — ADR-076) |
| Theme rotator (anti-repetition) | — | **Superseded** per ADR-087 (no evidence of value over TensionTracker + ADR-080 narrative-weight traits) |
| Mood-keyed tracks (string-keyed) | per `audio.yaml` | 7 core moods + per-pack `mood_aliases` (consumer not yet wired — ADR-033 P3) |

### Observability (ADR-058 / ADR-090)

| Feature | Module | Notes |
|---------|--------|-------|
| OTEL span catalog | `sidequest.telemetry.spans/` package — domain submodules: `agent`, `asset_url`, `audio`, `barrier`, `catch_up`, `chargen`, `chart`, `clock`, `combat`, `compose`, `content`, `continuity`, `course`, `dice`, `disposition`, `dogfight`, `emitter`, `encounter`, `interior`, `inventory`, `lobby`, `local_dm`, `lore`, `magic`, `merchant`, `monster_manual`, `mp`, `namegen`, `narrator`, `narrator_streaming`, `npc`, `opening`, `orchestrator`, `persistence`, `pregen`, `projection`, `rag`, `region_state`, `reminder`, `render`, `rig`, `room_state`, `scenario`, `scrapbook`, `script_tool`, `state_patch`, `trope`, `turn`, `world` | 50+ named spans (vs. ~10 Rust-side); `_core.SPAN_ROUTES` mutated by domain submodules at import |
| Phase timing | `telemetry.phase_timing` | Per-phase timing decorators |
| OTEL leak audit | `telemetry.leak_audit` | Python-era addition; verifies span hygiene |
| OTEL setup + Jaeger exporter | `telemetry.setup` | Story 45-41 — exporter flow fix; Jaeger now receives spans (ADR-090 partial) |
| Validator pipeline | `telemetry.validator` | `patch_legality_check`, `entity_reference_check`, etc. registered checks |
| TurnRecord pipeline | `telemetry.turn_record` | Async TurnRecord delivery to validator subscribers |
| Watcher endpoint | `/ws/watcher` (`server.watcher` + `server.emitters`) + `telemetry.watcher_hub` | Streaming telemetry to GM Mode |
| GM Mode dashboard | UI `Dashboard/` (`DashboardApp`, `DashboardHeader`, `DashboardTabs`) + tabs (`ConsoleTab`, `EncounterTab`, `LoreTab`, `PromptTab`, `StateTab`, `SubsystemsTab`, `TimelineTab`, `TimingTab`) + charts (`DonutChart`, `FlameChart`, `Histogram`, `ScatterPlot`, `TokenBarChart`) | **Live (partial)** — ADR-090 restoration ongoing; tabs and charts ported |
| Dashboard view route | `server.dashboard` | `/dashboard` route |
| Subsystem coverage tracker | partial — `agents/subsystems/` framework only | `CoverageGap` watcher event **dark** (ADR-087 RESTORE P1) |
| Watcher socket | `useWatcherSocket` | Client subscribes to GM mode telemetry |

### Player UI

| Feature | Component | Notes |
|---------|-----------|-------|
| GameBoard widget shell | `GameBoard/GameBoard.tsx` + `widgetRegistry` + `WidgetWrapper` + `BackgroundCanvas` + `MobileTabView` | Modular widget layout system |
| Widgets | `GameBoard/widgets/`: `AudioWidget`, `CharacterWidget`, `ConfrontationWidget`, `ImageGalleryWidget`, `InventoryWidget`, `KnowledgeWidget`, `MapWidget`, `NarrativeWidget`, `ScrapbookGallery`, `ShipWidget` | Each panel is a registered widget |
| GameBoard hotkeys / layout | `useGameBoardHotkeys` + `useGameBoardLayout` + `useLayoutMode` | P/C/I/M/J toggles + responsive layout |
| Party status panel | `PartyPanel` (`CharacterPanel`) | Portraits, status effects, Edge bars |
| Character sheet | `CharacterSheet` | Narrative-voiced per ADR-040; Edge/Composure replacing HP |
| Inventory panel | `InventoryPanel` + `InventoryWidget` | Items by type, equipped, gold |
| Map overlay | `MapOverlay` + `Automapper` + `DungeonMapRenderer` | Region nodes/connections (live world-map fog-of-war retired 2026-04-28) |
| Tactical grid renderer | `TacticalGridRenderer` + `tacticalGridFromWire` | SVG cell render (Epic 29 work shipped); engine deferred per ADR-071 |
| Journal/handouts | `JournalView` + `KnowledgeJournal` | KnownFacts by category + handout thumbnails |
| Combat overlay | (within `ConfrontationOverlay`) | Enemy state, beat surface |
| Confrontation overlay | `ConfrontationOverlay` + `InlineDiceTray` | Momentum, beats; reads live state mirror; mounts inline dice tray |
| Ledger panel | `LedgerPanel` | Magic/Edge ledger bars; reacts to `CONFRONTATION_OUTCOME` |
| Generic resource bar | `GenericResourceBar` | Reused across magic, edge, faction-aligned pools |
| Sensitivities section | `SensitivitiesSection` | Player-facing content sensitivities |
| Slash commands | `useSlashCommands` | /inventory, /character, /quests, /journal, /help, /tone |
| Server-side slash router | `sidequest.game.commands` | /status, /inventory, /map, /save, /tone, /gm suite (Python-era home) |
| Keyboard shortcuts | `GameLayout` | P/C/I/M/J toggles, Space, Escape |
| Responsive layout | `useBreakpoint` + `useLayoutMode` | Mobile/tablet/desktop |
| Genre theming | `ThemeProvider` + `useGenreTheme` | CSS vars from pack config (ADR-079); per-pack `client_theme.css` honored |
| Audio controls | `AudioStatus` + `useAudio` | Per-channel volume/mute/now-playing |
| Auto-reconnect | `ConnectScreen` + `ReconnectBanner` + `OfflineBanner` | localStorage session persistence |
| Multiplayer turn banner | `MultiplayerTurnBanner` + `MultiplayerSessionStatus` | Active turn-taker visibility |
| Peer reveals | `PeerRevealList` + `usePeerReveals` + `usePeerEventCache` + `peerEventStore` | Per-player asymmetric reveal stream |
| Peer events cache | `lib/peerEventStore` | Local store of cross-player observations |
| Narrative segments / streaming | `lib/narrativeSegments` + `providers/streamingNarration` | Two-message NARRATION/NARRATION_END atomic commit |
| Narration cards / focus / scroll | `NarrationCards` + `NarrationFocus` + `NarrationScroll` + `NarrativeRenderers` | Layered narration renderers |
| Action reveal / queue | `protocol.ACTION_REVEAL`, `ACTION_QUEUE` + `handlers.action_reveal` | Sealed-letter declaration reveal |
| Yield button | `YieldButton` | Voluntary turn yield wire |
| Image bus | `providers/ImageBusProvider` | Image pub/sub for widgets |
| Game state provider | `providers/GameStateProvider` | Shared state mirror context |
| Local prefs | `useLocalPrefs` | Per-player persisted preferences |
| Display name resolver | `useDisplayName` | Genre-aware display formatting |
| Running header | `useRunningHeader` | Header bar reacts to state mirror |
| Error boundary | `ErrorBoundary` | UI-level error fence |

### 3D Dice (ADR-074 / ADR-075)

| Feature | Module | Status |
|---------|--------|--------|
| Dice resolution protocol | `protocol.dice` + `protocol.DICE_REQUEST/THROW/RESULT` + `handlers.dice_throw` + `server.dispatch.dice` + `game.dice` | **Live** — ADR-074 promoted to accepted/live 2026-05-02 |
| Three.js + R3F + Rapier dice scene | `sidequest-ui/src/dice/{DiceScene,DiceOverlay,DiceSpikePage,InlineDiceTray}` + `d4/d6/d10/d12/d20.ts` | **Live (partial)** — ADR-075 promoted accepted/partial 2026-05-02 |
| Inline dice tray | `InlineDiceTray.tsx` mounted in `ConfrontationOverlay.tsx:325` | Architecture pivot from overlay → inline (auto-roll) |
| Dice theme | `diceTheme.ts` + `replayThrowParams.ts` | Default white-with-black |
| Dice throw gesture | `useDiceThrowGesture` | Click-and-auto-roll (gesture pivot) |
| Per-genre `dice.yaml` theming | — | **Dark (polish)** — zero packs declare; default ships for all (ADR-087 P3) |

### Dogfight (ADR-077)

| Feature | Module | Status |
|---------|--------|--------|
| Sealed-letter cross-product resolution | `server.dispatch.sealed_letter` + `narration_apply.py:1176` (`ResolutionMode.sealed_letter_lookup` branch) | **Live** — promoted to accepted/live 2026-05-02 |
| Dogfight content | `sidequest-content/genre_packs/space_opera/dogfight/` (descriptor_schema, interactions_mvp, interactions_tail_chase, maneuvers_mvp, pilot_skills) | **Live** |
| SOUL gate exclusion | live | In place |
| Test coverage | `tests/genre/test_dogfight_content_loading.py` | Live |

### Input Handling & Safety

| Feature | Module | Notes |
|---------|--------|-------|
| Input sanitization | `protocol.sanitize` + `agents.prompt_redaction` | Strips injection attempts at protocol boundary (ADR-047) |
| Lethality arbiter | `agents.lethality_arbiter` + `genre.lethality_policy_loader` | Policy-driven verdict on lethality claims (Python-era addition; not in Rust) |
| LocalDM decomposer | `agents.local_dm` (DORMANT on live path) + `corpus.miner` | Six modules carry DORMANT marker docstrings; offline-only corpus extraction (decision dated 2026-04-28) |
| Corpus mining CLIs | `cli.corpusmine`, `cli.corpusdiff`, `cli.corpuslabel` + `corpus.{diff,going_forward,miner,negatives,save_reader,schema,writer}` | Going-forward corpus capture pipeline; reserved wire kinds (`DISPATCH_PACKAGE`, `NARRATOR_DIRECTIVE_USED`, `VERDICT_OVERRIDE`) ride along |
| Verdict override / directive used | `protocol.{VERDICT_OVERRIDE, NARRATOR_DIRECTIVE_USED, DISPATCH_PACKAGE}` | Reserved kinds for going-forward corpus capture (Group B/C); not yet emitter-reachable for all paths |

### Genre Pack Modeling (Decomposed)

| Feature | Module | Notes |
|---------|--------|-------|
| Genre pack schema | `genre.models.pack` (`PackConfig`) | Top-level pack metadata |
| Rules / beats | `genre.models.rules` | Beats, edge_delta, target_edge_delta, resource_deltas |
| Axes / archetype axes | `genre.models.axes` + `archetype_axes` + `archetype_constraints` + `archetype_funnels` | Three-mode chargen + funnels |
| Archetypes | `genre.models.archetype` + `genre.archetype.{resolved,shim}` | Resolved archetype + shim for legacy callers |
| Character + chassis + inventory | `genre.models.{character,chassis,inventory}` | |
| Cultures | `genre.models.culture` + per-pack `cultures.yaml` + `corpus/` directory | ADR-091 culture-corpus + Markov |
| Names | `genre.names.{generator,markov,thresholds}` | Per-culture Markov; min-pool guard + thin-corpus audit (story 45-28) |
| Lethality | `genre.models.lethality` | |
| Audio | `genre.models.audio` | mood_aliases (P3 polish gap) |
| Visibility / projection | `genre.models.visibility` + `visibility_baseline.yaml` + `projection.yaml` | Per-player visibility config |
| Lore / legends | `genre.models.{lore,legends}` | |
| OCEAN / NPC traits | `genre.models.{ocean,npc_traits,authored_npc}` | |
| Theme | `genre.models.theme` + `theme.yaml` + `client_theme.css` | |
| Tropes | `genre.models.tropes` + `tropes.yaml` | |
| Progression / advancement | `genre.models.{progression,advancement}` | |
| Narrative axis / scenario | `genre.models.{narrative,scenario}` | |
| Rigs world | `genre.models.rigs_world` | Sibling-of-magic rig framework anchor |
| World | `genre.models.world` + per-world `world.yaml` | |

### Server Dispatch Package (ADR-063 partly executed)

| Handler | Module | Notes |
|---------|--------|-------|
| Char creation resolve | `server.dispatch.char_creation_resolve` | Final resolve step |
| Chargen loadout | `server.dispatch.chargen_loadout` | Loadout dispatch; double-init dedup story 45-12 |
| Chargen summary | `server.dispatch.chargen_summary` | |
| Combat brackets | `server.dispatch.combat_brackets` | |
| Confrontation | `server.dispatch.confrontation` | Pillar-1/2 ADR-033 path |
| Culture context | `server.dispatch.culture_context` | Per-culture narrator context |
| Dice | `server.dispatch.dice` | ADR-074 dispatch |
| Encounter lifecycle | `server.dispatch.encounter_lifecycle` | XP path partial stub |
| Lore embed | `server.dispatch.lore_embed` | Per-turn embedding fan-out |
| Opening | `server.dispatch.opening` | Session opener narration |
| Scenario bind | `server.dispatch.scenario_bind` | Bottle-episode binding |
| Sealed letter | `server.dispatch.sealed_letter` | Phase-5 sealed-letter dispatch |
| Yield action | `server.dispatch.yield_action` | Edge debit on yield |

### Handlers Package (Top-Level)

| Handler | Module | Notes |
|---------|--------|-------|
| Action reveal | `handlers.action_reveal` | Sealed-letter reveal handler |
| Character creation | `handlers.character_creation` | Replaces inline session_handler logic |
| Connect | `handlers.connect` | Connect handshake |
| Course intent | `handlers.course_intent` | Orbital chart course-intent inbound |
| Dice throw | `handlers.dice_throw` | DICE_THROW inbound |
| Orbital intent | `handlers.orbital_intent` | ORBITAL_INTENT inbound |
| Player action | `handlers.player_action` | PLAYER_ACTION inbound (the live turn entry point) |
| Player seat | `handlers.player_seat` | Lobby seat claim |
| Session event | `handlers.session_event` | Session event dispatch |
| Yield action | `handlers.yield_action` | YIELD inbound |

### CLIs (`pyproject.toml [project.scripts]`)

| CLI | Module | Status |
|-----|--------|--------|
| `sidequest-server` | `sidequest.server.app:main` | **Live** — the only registered `[project.scripts]` entry point |
| `python -m sidequest.cli.namegen` | `cli/namegen/namegen.py` (22.7K LOC) + `__main__.py` | **Code present, runnable as module; not wired into server** — no `[project.scripts]` entry; server doesn't dispatch (ADR-087 REWIRE P0) |
| `sidequest-encountergen` | `cli/encountergen/__init__.py` stub | **Empty** (ADR-087 RESTORE P0) |
| `sidequest-loadoutgen` | `cli/loadoutgen/__init__.py` stub | **Empty** (ADR-087 RESTORE P0) |
| `sidequest-validate` | `cli/validate/projection_check.py` only | **Partial** — projection check shipped; broader schema validation owed (ADR-087 RESTORE P2) |
| `sidequest-promptpreview` | `cli/promptpreview/__init__.py` stub | **Empty** (ADR-087 RESTORE P1) |
| `python -m sidequest.cli.corpusmine` | `cli/corpusmine/` + `__main__.py` | **Live** — corpus mining for LocalDM (module-runnable; not registered in `[project.scripts]`) |
| `python -m sidequest.cli.corpusdiff` | `cli/corpusdiff/` + `__main__.py` | **Live** (module-runnable) |
| `python -m sidequest.cli.corpuslabel` | `cli/corpuslabel/` + `__main__.py` | **Live** (module-runnable) |

---

## Dark / Partial (ADR-087 Restoration Roster)

Verdicts and tiers per ADR-087 (last sweep 2026-05-02).

### P0 — this sprint or next (5 items)

| Subsystem | ADR-087 verdict |
|-----------|------------------|
| ADR-059 pregen dispatch (server invokes namegen/encountergen/loadoutgen at turn-time) | RESTORE |
| `sidequest-namegen` rewire (entry point + dispatch integration) | REWIRE |
| `sidequest-encountergen` (currently empty stub) | RESTORE |
| `sidequest-loadoutgen` (currently empty stub) | RESTORE |
| ADR-092 scene fixture hydrator + `POST /dev/scene/{name}` (supersedes ADR-069) | RESTORE |

> Item 6 (Confrontation Engine port-drift VERIFY) was demoted from P0 to P3 polish on 2026-05-02 — Pillars 1+2 verified live; only `mood_aliases` consumer remains (now P3).

### P1 — within current epic window (8 items)

Trope engine (ADR-018), NPC disposition Attitude transitions (ADR-020), sealed-letter dispatch handler (Phase-5 module landed; broader ADR-024/028 scope still partial), continuity validator, patch legality gate (currently *partial* in `telemetry/validator.py`), subsystem coverage tracker (`CoverageGap` events), `sidequest-promptpreview` CLI, inventory extractor (VERIFY first).

### P2 — design-ready, next-epic candidate (11 items)

Gossip engine (ADR-053), accusation logic (ADR-053), genie wish consequence engine (ADR-041), OCEAN shift proposals (ADR-042), chase engine (ADR-017 — affects road_warrior and space_opera Ship Block), catch-up dispatch handler, lore filter, `sidequest-validate` CLI expansion, scene relevance validator (REDESIGN under ADR-086), room graph per-transition mechanics + new map wire message (ADR-055), Edge/Composure Epic 39 wiring + push-currency rituals (ADR-078).

### P3 — flavor / low urgency (4 items)

Beat filter, test-support helpers (VERIFY), `mood_aliases` alias-chain consumer (ADR-033 Pillar 3), per-genre `dice.yaml` theming (ADR-075).

### Deferred — markers confirmed (8 items)

Affinity progression (P6-deferred at `game/character.py:55-64`), advancement effect variants v1 (ADR-081 accepted/deferred — upstream-blocked on Edge/Composure Epic 39), Edge/Composure Epic 39 wiring (rides P2 item 25), tactical grid engine (ADR-071 Proposed — protocol live), 3D dice rendering polish (ADR-075 partial), merchant system (no ADR — write one first), combat mechanics detail beyond Epic 28 restoration.

### Superseded / collapsed (4 items)

Theme rotator (no demonstrated value; SUPERSEDED), scrapbook standalone (collapse into daemon — pending VERIFY), separate narrator/troper/resonator/world_builder agents (collapsed under ADR-067), 14-tool abstraction (collapsed under ADR-059 — and ADR-057 deprecated 2026-05-02 as infeasible under ADR-001).

### Do not restore

Speculative prerendering (ADR-044 historical 2026-05-02 — TTS-deprecated premise), conlang morpheme glossary (ADR-043 superseded by ADR-091 culture-corpus + Markov).

---

## Sprint 3 Snapshot (Active)

Two epics open: Epic 45 (Playtest 3 closeout) and Epic 47 (Magic system + Rig MVP).

**Epic 45 — three lanes:**
- **(A) MP correctness** — sealed-letter shared-world delta, turn-barrier fix, momentum sync (45-1, 45-2, 45-3 done)
- **(B) State write-back hygiene** — 21 stories carrying placeholder cleanup, content-drift triage, OTEL/tuning work (45-4 through 45-23 done)
- **(C) UI/cleanup tax + tuning + render observability** — chargen polish, web-socket tuning, render trigger policy, image silent-fallback teardown, Z-Image high-fidelity tier, OTEL exporter fix (45-24 through 45-42 done)

Plus port-drift wave-work on snapshot split-brain: 45-45 (Wave 1: dedup+rename), 45-47 (Wave 2A: NPC pool/state split) done; 45-48 (Wave 2B: location derivation), 45-46 (Wave 1 cleanup), 45-52 (Wave 2A cleanup) backlog. Orrery v2 visual restoration (ADR-094) shipped via 45-43 + 45-40. ADR-066 §8 narrator session crash recovery shipped (45-50); §7/§9/§10 proactive watchdog backlog (45-51).

**Epic 47 — Magic system landed in waves:** Phase 4 verification + smoke (47-1 done, 47-2 backlog), Phase 5 confrontations wired (47-3 done — five confrontations live), Rig MVP Phase C tea-brew confrontation (47-4 done), Phase 6 multiplayer playtest (47-5 backlog), tea-ritual three-layer fix (47-6 done), magic state bars uninit warning (47-7 backlog), Coyote Object salvage hooks design (47-8 backlog).

Backlog of 11 stories remains as of 2026-05-05.

---

## Genre Pack Status (Pointer)

7 pack directories in `sidequest-content/genre_packs/` but only **5 are functionally loadable**: `caverns_and_claudes`, `elemental_harmony`, `mutant_wasteland`, `space_opera`, `victoria`. The `heavy_metal` and `spaghetti_western` production directories are empty shells; their YAMLs live in `genre_workshopping/`. Four other packs (`low_fantasy`, `neon_dystopia`, `pulp_noir`, `road_warrior`) are workshop-only.

`space_opera` ships dogfight content under `dogfight/` (descriptor_schema, interactions_mvp, interactions_tail_chase, maneuvers_mvp, pilot_skills) and the `coyote_star` world is the Magic + Rig MVP flagship (ADR-094 orrery callouts; orbital chart system).

Full pack-by-pack breakdown lives at [`docs/genre-pack-status.md`](genre-pack-status.md).

---

## Pre-Port Inventory (Historical)

Earlier revisions of this document tabulated Sprint 1/Sprint 2 work against Epics 1–26 of the **Rust** workspace (`sidequest-api`). That tracker context is preserved in the sprint archive (`sprint/archive/`) and in the Rust-tree commit history at <https://github.com/slabgorb/sidequest-api>. Subsystem-level mapping from those epics to the current Python tree lives in:

- `docs/adr/README.md` (Rust → Python translation table)
- `docs/port-drift-feature-audit-2026-04-24.md` (per-subsystem landing audit)
- `docs/adr/087-post-port-subsystem-restoration-plan.md` (verdict + tier for each non-parity row)

---

## What's Playtest-Ready Today (Post-Port)

The full game loop is wired end-to-end in Python: connect → create character → play → narrate → render images → play music. Multiplayer works with turn barriers, adaptive batching, party action composition, perception rewriting, and the post-Sprint-3 sealed-letter shared-world delta. The unified narrator (ADR-067) handles exploration, dialogue, combat narration, and chase narration through one persistent Opus session; auxiliary subsystem agents (chassis_voice, distinctive_detail, npc_agency, reflect_absence) run off the critical path. Pacing engine shapes delivery speed and narrator length via TensionTracker. Lore RAG, OCEAN profiles, footnoted narration with journal callback, and projection-filtered per-player views are all live.

**The big new feature surfaces since the port:**
- **Magic system** — plugin protocol, ledger bars, five wired confrontations, validator with severity-tiered flags. Coyote Star + heavy_metal references; LedgerPanel reacts on `CONFRONTATION_OUTCOME`.
- **Edge / Composure** — Edge primitive on `CreatureCore` replaces HP across the codebase (45-35); `apply_edge_delta` wired from yield + session paths; threshold helper extracted; advancement-effect data shapes loaded.
- **Orbital chart** — server-side SVG renderer, course plotting (eta + Δv), conjunction beats, three-strategy label placement (ADR-094); UI in `OrbitalChart/` with HUD strips matching Star Wars palette.
- **Interior / Ship widget** — `voidborn_freighter` (Kestrel) 2x2 chassis interior SVG renderer; client `ShipWidget`.
- **3D dice** — Three.js + R3F + Rapier inline tray mounted in ConfrontationOverlay.
- **Dogfight** — sealed-letter cross-product resolution live; space_opera content shipping.
- **GameBoard widget architecture** — modular widget shell with registry; replaces fixed-panel layout.
- **Dashboard restoration (ADR-090)** — eight tabs (Console, Encounter, Lore, Prompt, State, Subsystems, Timeline, Timing) plus five chart primitives; OTEL exporter to Jaeger flowing.
- **Cloud media** — daemon R2 writer; `just serve` + `just tunnel` for prod deployment.
- **Decomposed projection** — eleven-module `game/projection/` package with predicate validators and invariants.
- **Decomposed telemetry** — 50+ span modules in `telemetry/spans/` (vs. ~10 in Rust).

OTEL coverage is the strongest it has ever been. The biggest known gaps for Keith-as-player and Sebastien (mechanics-first) remain on the ADR-087 restoration roster: trope engine, disposition Attitude transitions, continuity validator, and pregen dispatch. Each is what makes the difference between a narrator that improvises convincingly and a narrator the GM panel can actually keep honest. CLAUDE.md says it plain: _"The GM panel is the lie detector."_ Sprint 3 closes the playtest debt; the next sprint inherits ADR-087's P0 tier.

**Best playtest experience today:** Multiplayer session in `caverns_and_claudes` (most worlds), `elemental_harmony` (richest audio), `victoria` (most distinctive mechanics + curated music), or `space_opera/coyote_star` (orbital chart + magic + rig MVP — flagship for Epic 47 work). Full media pipeline, faction-driven world, OCEAN-flavored NPCs, footnoted narration with journal, confrontation engine with genre-typed resource pools where wired, Edge/Composure replacing HP, magic ledger bars and five wired confrontations.
