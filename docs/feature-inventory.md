# SideQuest Feature Inventory

**Last updated:** 2026-04-01
**Sprint 1:** Bootstrap Rust workspace (completed — 85 stories, 672/726 points)
**Sprint 2:** Multiplayer Works For Real (active — 11/87 points)

## Legend

- **Done & Wired** — Implemented and connected end-to-end (API + UI + Daemon)
- **Done (API only)** — Implemented in Rust but not yet exercised in a live session
- **In Progress** — Current sprint work
- **Planned** — Backlog, not yet started

**Wiring diagrams:** See [`docs/wiring-diagrams.md`](wiring-diagrams.md) for end-to-end signal traces (Mermaid) showing every feature's path from UI to storage.

---

## Done & Wired (End-to-End Working)

These features work from player input through to rendered output.

### Core Game Loop (Epics 1-2, complete)

| Feature | API | UI | Daemon | Notes |
|---------|-----|-----|--------|-------|
| WebSocket connection | sidequest-server | useGameSocket | — | Real-time bidirectional |
| REST genres endpoint | /api/genres | ConnectScreen | — | Genre + world selection |
| Session lifecycle | Session actor | ConnectScreen → GameLayout | — | Connect → Create → Play |
| Character creation | CharacterBuilder state machine | CharacterCreation component | — | Multi-scene, genre-driven |
| Orchestrator turn loop | Intent → Agent → Patch → Broadcast | NarrativeView | — | Full turn cycle |
| Intent classification | Two-tier (Haiku + Narrator) | — | — | ADR-032 |
| Agent dispatch | 7 agents (Narrator, WorldBuilder, CreatureSmith, Ensemble, Dialectician, IntentRouter, Troper) | — | — | Claude CLI subprocess |
| State patching | JSON delta patches | useStateMirror | — | Combat/chase/world |
| Narration streaming | NARRATION_CHUNK messages | NarrativeView (markdown) | — | DOMPurify sanitized |
| SQLite persistence | Save/load GameSnapshot | — | — | Session recovery |
| Trope engine | Tick progression, beat injection | — | — | World + genre tropes |
| Genre pack loading | sidequest-genre crate | ThemeProvider (CSS vars) | — | 7 packs, validated |
| CORS support | axum middleware | Vite proxy | — | Dev + prod |

### Media Pipeline (Epic 4, complete)

| Feature | API | UI | Daemon | Notes |
|---------|-----|-----|--------|-------|
| Image generation | Subject extractor → Render queue | IMAGE display | Flux.1 (schnell + dev) | 6 tiers: scene, portrait, landscape, text, cartography, tactical |
| Beat filter | Suppress low-drama renders | — | — | drama_weight threshold |
| Speculative prerender | Queue during voice playback | — | — | Hash-based cache dedup (ADR-044) |
| TTS voice synthesis | Voice routing, text segmentation | useVoicePlayback | Kokoro (54 voices) | Streaming delivery |
| Character voice mapping | Genre pack voice presets | — | Voice router + effects | Per-character voices |
| Music direction | Mood extraction from narration | useMusicPlayer | Audio mixer | AUDIO_CUE messages |
| 3-channel audio | Music/SFX/ambience commands | AudioStatus component | pygame mixer | Ducking during speech (ADR-045) |
| Theme rotation | Anti-repetition track selection | — | Audio rotator | Mood-based |

### Observability (Epic 3, complete)

| Feature | API | UI | Daemon | Notes |
|---------|-----|-----|--------|-------|
| Agent telemetry | #[instrument] spans | GM Mode panel | — | JSON tracing subscriber |
| TurnRecord pipeline | mpsc channel | — | — | Async validation |
| Patch legality checks | Deterministic rule validation | — | — | Catches bad patches |
| Entity reference validation | Narration ↔ GameSnapshot | — | — | Catches hallucinations |
| Subsystem exercise tracker | Agent invocation histogram | — | — | Coverage gaps |
| Watcher endpoint | /ws/watcher | useWatcherSocket | — | Streaming telemetry |
| GM Mode | — | GMMode component | — | Event stream, trope timeline, state inspector |

### Player UI (from sidequest-ui)

| Feature | Component | Notes |
|---------|-----------|-------|
| Party status panel | PartyPanel | Portraits, HP bars, status effects |
| Character sheet | CharacterSheet | Stats, abilities, backstory |
| Inventory panel | InventoryPanel | Items by type, equipped state, gold |
| Map overlay | MapOverlay | SVG nodes, connections, fog of war |
| Journal/handouts | JournalView | Thumbnail grid, lightbox viewer |
| Combat overlay | CombatOverlay | Enemy HP, turn order |
| Slash commands | useSlashCommands | /inventory, /character, /quests, /journal, /help |
| Push-to-talk | usePushToTalk | Record → Whisper transcribe → preview → send (disabled, ADR-054) |
| WebRTC voice chat | useVoiceChat + PeerMesh | Disabled — echo feedback loop (ADR-054) |
| Keyboard shortcuts | GameLayout | P/C/I/M/J toggles, Space, Escape |
| Responsive layout | useBreakpoint | Mobile/tablet/desktop |
| Genre theming | ThemeProvider + useGenreTheme | CSS vars from pack config |
| Audio controls | AudioStatus | Per-channel volume, mute, now playing |
| Auto-reconnect | ConnectScreen | localStorage session persistence |

### Multiplayer (Epic 8, complete)

| Feature | Story | Notes |
|---------|-------|-------|
| Multi-client sessions | 8-1 | player_id mapping |
| Turn barrier | 8-2 | Wait for all players (ADR-036) |
| Adaptive action batching | 8-3 | 3s for 2-3, 5s for 4+ |
| Party action composition | 8-4 | Multi-character PARTY ACTIONS block |
| Turn modes | 8-5 | FREE_PLAY, STRUCTURED, CINEMATIC (ADR-036) |
| Perception rewriter | 8-6 | Per-character narration variants (ADR-028) |
| Guest NPC players | 8-7 | Human-controlled NPCs |
| Catch-up narration | 8-8 | Mid-session join snapshot |
| Turn reminders | 8-9 | Idle player timeout |

### Pacing & Drama (Epic 5, complete)

| Feature | Story | Notes |
|---------|-------|-------|
| TensionTracker (dual-track) | 5-1 | Gambler's ramp + HP stakes |
| Combat event classification | 5-2 | Boring/dramatic categorization |
| Drama weight computation | 5-3 | max(action, stakes) + spike decay |
| Pacing hint generation | 5-4 | drama_weight → sentence count |
| Drama-aware delivery | 5-5 | INSTANT/SENTENCE/STREAMING modes |
| Quiet turn detection | 5-6 | Escalation beat injection |
| Pacing wired to orchestrator | 5-7 | drama_weight flows through turn pipeline |
| Genre-tunable thresholds | 5-8 | Per-pack drama breakpoints |
| Two-tier intent classification | 5-9 | Haiku + Narrator ambiguity resolution |
| Prompt framework wiring | 5-10 | ContextBuilder replaces format! concat |

### Active World (Epic 6, complete)

| Feature | Story | Notes |
|---------|-------|-------|
| Scene directive formatter | 6-1 | Fired beats + hints + stakes |
| MUST-weave instruction | 6-2 | Narrator prompt positioning |
| Engagement multiplier | 6-3 | Trope progression scaling |
| FactionAgenda model | 6-4 | Faction goals + urgency |
| Wire faction agendas | 6-5 | Scene injection |
| World materialization | 6-6 | Campaign maturity levels |
| Faction agendas (mutant_wasteland) | 6-7 | Genre pack content |
| Faction agendas (elemental_harmony) | 6-8 | Genre pack content |
| Wire scene directives to orchestrator | 6-9 | Per-turn injection |

### Character Depth (Epic 9, 12/13 complete)

| Feature | Story | Status | Notes |
|---------|-------|--------|-------|
| AbilityDefinition model | 9-1 | Done | Genre-voiced descriptions |
| Ability perception | 9-2 | Done | Involuntary triggers in narrator |
| KnownFact model | 9-3 | Done | Play-derived knowledge |
| Known facts in prompt | 9-4 | Done | Tiered injection by relevance |
| Narrative character sheet | 9-5 | Done | Genre-voiced display |
| Slash command router (server) | 9-6 | Done | Server-side /command intercept |
| Core slash commands (server) | 9-7 | Done | /status, /inventory, /map, /save |
| GM commands | 9-8 | Done | /gm set, teleport, spawn, dmg |
| Tone command | 9-9 | Done | Adjust genre axes |
| Wire to React client | 9-10 | Done | CHARACTER_SHEET message |
| Structured footnote output | 9-11 | Done | NarrationPayload with footnotes[] |
| Footnote rendering | 9-12 | Done | Superscript markers, discovery/callback styling |
| Journal browse view | 9-13 | In Progress | KnownFacts by category with genre voice |

### NPC Personality (Epic 10, complete)

| Feature | Story | Notes |
|---------|-------|-------|
| OCEAN profile fields | 10-1 | Five floats on NPC (0.0-10.0) |
| Genre archetype baselines | 10-2 | Default profiles per archetype |
| Behavioral summary | 10-3 | Scores → prompt text |
| Narrator reads OCEAN | 10-4 | Voice/behavior adjustment |
| OCEAN shift log | 10-5 | Personality change tracking |
| Agent proposes shifts | 10-6 | Event-driven evolution (ADR-042) |
| Agreeableness → Disposition | 10-7 | Feeds existing disposition system |
| Backfill genre packs | 10-8 | OCEAN profiles on all archetypes |

### Lore & Language (Epic 11, complete)

| Feature | Story | Notes |
|---------|-------|-------|
| LoreFragment model | 11-1 | Indexed narrative facts |
| LoreStore | 11-2 | In-memory indexed collection |
| Lore seed | 11-3 | Bootstrap from genre pack |
| Lore in agent prompts | 11-4 | Relevant fragment injection |
| Lore accumulation | 11-5 | World state writes new fragments |
| Semantic retrieval | 11-6 | Embedding-based RAG (ADR-048) |
| Morpheme glossary | 11-7 | Conlang morphemes (ADR-043) |
| Name bank generation | 11-8 | Glossed names from language rules |
| Narrator name injection | 11-9 | Consistent naming |
| Language as KnownFact | 11-10 | Transliteration growth |

---

## In Progress (Sprint 2)

### Sealed Letter Turn System (Epic 13, 2/10 complete)

Simultaneous input collection with player visibility. Replaces free-for-all turns with a sealed letter pattern.

| Feature | Story | Status | Points | Notes |
|---------|-------|--------|--------|-------|
| Single narrator call per barrier turn | 13-8 | Done | 5 | Resolution lock, broadcast to others |
| Barrier timeout handling | 13-9 | Done | 3 | Force-resolve missing, broadcast notification |
| Barrier error handling | 13-10 | Ready | 3 | Propagate add_player errors, fix disconnect race |
| Turn collection UI | 13-1 | Ready | 5 | Pending/submitted status per player |
| Server-side sealed collection | 13-2 | Ready | 5 | Hold actions until barrier met, batch-submit |
| Action reveal broadcast | 13-3 | Ready | 3 | Show submitted actions to full party |
| Timeout fallback with notification | 13-4 | Ready | 3 | Auto-fill missing, notify who was auto-resolved |
| Turn mode indicator in UI | 13-5 | Ready | 2 | Free Play / Structured / Cinematic display |
| DM override for turn resolution | 13-6 | Ready | 3 | Force-resolve or extend timeout |
| Sealed letter integration test | 13-7 | Ready | 3 | 4-player e2e: submit, timeout, reveal |

### Multiplayer Session UX (Epic 14, 0/9 complete)

Post-playtest UX fixes: spawn, visibility, text tuning, chargen polish.

| Feature | Story | Status | Points | Notes |
|---------|-------|--------|--------|-------|
| Party co-location at session start | 14-1 | Ready | 5 | Configurable spawn point |
| Player location on character sheet | 14-2 | Ready | 2 | current_location in PARTY_STATUS |
| Text length slider | 14-3 | Ready | 3 | Concise / standard / verbose |
| Vocabulary level slider | 14-4 | Ready | 3 | Accessible / literary / epic |
| Character generation back button | 14-5 | Ready | 3 | Edit choices before final submit |
| Image pacing throttle | 14-6 | Ready | 3 | Configurable cooldown between images |
| Image scene relevance filter | 14-7 | Ready | 5 | Validate art prompt matches scene |
| Sound slider labels | 14-8 | Ready | 1 | Visible labels on all audio sliders |
| Footnote inline references | 14-9 | Ready | 2 | Superscript links to numbered footnotes |

### Playtest Debt (Epic 15, 0/5 complete)

Technical debt from 2026-03-29 post-playtest audit.

| Feature | Story | Status | Points | Notes |
|---------|-------|--------|--------|-------|
| Remove dead code | 15-1 | Ready | 2 | if-false blocks, stale comments, duplicates |
| Wire OCEAN shift proposals | 15-2 | Ready | 3 | Events trigger personality evolution (ADR-042) |
| Voice/mic architecture | 15-3 | Ready | 5 | Solve TTS feedback loop (ADR-054) |
| Perception rewriter | 15-4 | Ready | 5 | Implement Blinded strategy as proof-of-concept |
| Daemon client typed API | 15-5 | Ready | 2 | Wire or remove stub types |

---

## Planned (Not Started)

### Epic 7: Scenario System — Bottle Episodes, Whodunit (P2, deferred)

**Note:** Core scenario mechanics (BeliefState, GossipEngine, ClueGraph, AccusationEvaluator) are implemented in sidequest-game but not yet wired to the orchestrator (ADR-053). Stories here cover wiring and integration.

| Feature | Story | Points | Notes |
|---------|-------|--------|-------|
| BeliefState model | 7-1 | 5 | Per-NPC knowledge bubbles |
| Gossip propagation | 7-2 | 5 | Claims spread, credibility decay |
| Clue activation | 7-3 | — | Semantic triggers |
| Accusation system | 7-4 | — | Evidence evaluation |
| NPC autonomous actions | 7-5 | — | Alibi, confess, flee |
| Scenario pacing | 7-6 | — | Turn-based pressure |
| Scenario archiver | 7-7 | — | Save/resume mid-scenario |
| Scenario scoring | 7-8 | — | Evidence metrics |
| ScenarioEngine wiring | 7-9 | — | Orchestrator integration |

### Epic 12: Cinematic Audio — Score Cue Variations (P2)

| Feature | Story | Points | Notes |
|---------|-------|--------|-------|
| Cinematic track variation selection | 12-1 | 5 | MusicDirector uses themed score cues |
| Per-variation crossfade durations | 12-2 | 2 | Overture fades slow, tension_build hits hard |
| Variation telemetry in watcher | 12-3 | 1 | Score cue selection visible in GM panel |

---

## Summary

| Category | Done | Total | Completion |
|----------|------|-------|------------|
| Epic 1: Workspace Scaffolding | 13/13 | 13 | 100% |
| Epic 2: Core Game Loop | 9/9 | 9 | 100% |
| Epic 3: Game Watcher | 9/9 | 9 | 100% |
| Epic 4: Media Integration | 12/12 | 12 | 100% |
| Epic 5: Pacing & Drama | 10/10 | 10 | 100% |
| Epic 6: Active World | 9/9 | 9 | 100% |
| Epic 7: Scenario System | 0/9 | 9 | 0% |
| Epic 8: Multiplayer | 9/9 | 9 | 100% |
| Epic 9: Character Depth | 12/13 | 13 | 92% |
| Epic 10: OCEAN Personality | 8/8 | 8 | 100% |
| Epic 11: Lore & Language | 10/10 | 10 | 100% |
| Epic 12: Cinematic Audio | 0/3 | 3 | 0% |
| Epic 13: Sealed Letter Turns | 2/10 | 10 | 20% |
| Epic 14: Session UX | 0/9 | 9 | 0% |
| Epic 15: Playtest Debt | 0/5 | 5 | 0% |
| **Total** | **103/138** | **138** | **75%** |

### What's Playtest-Ready Today

The full game loop is wired: connect → create character → play → narrate → render images → synthesize voice → play music. Multiplayer works with turn barriers, adaptive batching, and party action composition across all three turn modes. The GM watcher dashboard is live. All seven genre packs load with OCEAN personality profiles on every NPC archetype.

Pacing is fully wired — tension tracking, drama-aware delivery speed, quiet turn escalation, and genre-tunable thresholds all flow through the orchestrator. Active World features are complete: faction agendas inject into scenes, world materialization tracks campaign maturity, and trope engagement scales with progression.

Character depth is nearly complete: server-side slash commands (/status, /inventory, /map, /save, /gm), narrative character sheets, footnoted narration with KnownFact accumulation, and tone adjustment. Lore & Language is fully operational with semantic retrieval, conlang name generation, and narrator name injection.

**Best playtest experience:** Multiplayer session in any genre pack. Full media pipeline. Faction-driven world. OCEAN personality on NPCs. Footnoted narration with journal. Pacing engine shapes delivery speed and narrator length.

**Sprint 2 focus:** Sealed letter turn system (simultaneous action submission), multiplayer UX polish (spawn points, text/vocabulary sliders, chargen back button), and playtest debt cleanup.

**Not yet exercised:** Scenario/mystery mechanics (Epic 7, core mechanics implemented per ADR-053 but not yet wired), cinematic score cue variations (Epic 12), perception rewriter strategies, OCEAN shift proposal wiring into game flow.
