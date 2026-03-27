# SideQuest Feature Inventory

**Last updated:** 2026-03-27
**Sprint 1:** Bootstrap Rust workspace scaffolding (460/619 points)

## Legend

- **Done & Wired** — Implemented and connected end-to-end (API ↔ UI ↔ Daemon)
- **Done (API only)** — Implemented in Rust but not yet exercised in a live session
- **In Progress** — Current sprint work
- **Planned** — Backlog, not yet started

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
| Speculative prerender | Queue during voice playback | — | — | Hash-based cache dedup |
| TTS voice synthesis | Voice routing, text segmentation | useVoicePlayback | Kokoro (54 voices) | Streaming delivery |
| Character voice mapping | Genre pack voice presets | — | Voice router + effects | Per-character voices |
| Music direction | Mood extraction from narration | useMusicPlayer | Audio mixer | AUDIO_CUE messages |
| 3-channel audio | Music/SFX/ambience commands | AudioStatus component | pygame mixer | Ducking during speech |
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
| Push-to-talk | usePushToTalk | Record → Whisper transcribe → preview → send |
| WebRTC voice chat | useVoiceChat + PeerMesh | Peer-to-peer, echo cancellation |
| Keyboard shortcuts | GameLayout | P/C/I/M/J toggles, Space, Escape |
| Responsive layout | useBreakpoint | Mobile/tablet/desktop |
| Genre theming | ThemeProvider + useGenreTheme | CSS vars from pack config |
| Audio controls | AudioStatus | Per-channel volume, mute, now playing |
| Auto-reconnect | ConnectScreen | localStorage session persistence |

### Multiplayer (Epic 8, mostly complete)

| Feature | Story | Status | Notes |
|---------|-------|--------|-------|
| Multi-client sessions | 8-1 | Done | player_id mapping |
| Turn barrier | 8-2 | Done | Wait for all players |
| Adaptive action batching | 8-3 | Done | 3s for 2-3, 5s for 4+ |
| Party action composition | 8-4 | Done | Multi-character PARTY ACTIONS block |
| Turn modes | 8-5 | Done | FREE_PLAY, STRUCTURED, CINEMATIC |
| Perception rewriter | 8-6 | Done | Per-character narration variants |
| Guest NPC players | 8-7 | Done | Human-controlled NPCs |
| Catch-up narration | 8-8 | Done | Mid-session join snapshot |
| Turn reminders | 8-9 | Backlog | Idle player timeout |

---

## Done (API Only — Not Yet Wired or Exercised)

These features are implemented in Rust with passing tests but haven't been validated in a live playtest session.

### Pacing & Drama (Epic 5, in progress)

| Feature | Story | Status | Notes |
|---------|-------|--------|-------|
| TensionTracker (dual-track) | 5-1 | Done | Gambler's ramp + HP stakes |
| Pacing wired to orchestrator | 5-7 | Done | drama_weight flows through turn pipeline |
| Two-tier intent classification | 5-9 | Done | Haiku + Narrator ambiguity resolution |
| Prompt framework wiring | 5-10 | Done | ContextBuilder replaces format! concat |
| Combat event classification | 5-2 | In Progress | boring/dramatic categorization |
| Drama weight computation | 5-3 | Backlog | max(action, stakes) + spike decay |
| Pacing hint generation | 5-4 | Backlog | drama_weight → sentence count |
| Drama-aware delivery | 5-5 | Backlog | INSTANT/SENTENCE/STREAMING modes |
| Quiet turn detection | 5-6 | Backlog | Escalation beat injection |
| Genre-tunable thresholds | 5-8 | Backlog | Per-pack drama breakpoints |

### Active World (Epic 6, in progress)

| Feature | Story | Status | Notes |
|---------|-------|--------|-------|
| Scene directive formatter | 6-1 | Done | fired beats + hints + stakes |
| MUST-weave instruction | 6-2 | Done | Narrator prompt positioning |
| Engagement multiplier | 6-3 | Done | Trope progression scaling |
| FactionAgenda model | 6-4 | Backlog | Faction goals + urgency |
| Wire faction agendas | 6-5 | Backlog | Scene injection |
| World materialization | 6-6 | Backlog | Campaign maturity levels |
| Faction agendas (mutant_wasteland) | 6-7 | Backlog | Genre pack content |
| Faction agendas (elemental_harmony) | 6-8 | Backlog | Genre pack content |
| Wire scene directives to orchestrator | 6-9 | Backlog | Per-turn injection |

### Character Depth (Epic 9, started)

| Feature | Story | Status | Notes |
|---------|-------|--------|-------|
| AbilityDefinition model | 9-1 | Done | Genre-voiced descriptions |
| Ability perception | 9-2 | Backlog | Involuntary triggers in narrator |
| KnownFact model | 9-3 | Backlog | Play-derived knowledge |
| Known facts in prompt | 9-4 | Backlog | Character perception |
| Narrative character sheet | 9-5 | Backlog | Genre-voiced display |
| Slash command router (server) | 9-6 | Backlog | Server-side /command |
| Core slash commands (server) | 9-7 | Backlog | /status, /inventory, /map, /save |
| GM commands | 9-8 | Backlog | /gm set, teleport, spawn, dmg |
| Tone command | 9-9 | Backlog | Adjust genre axes |
| Wire to React client | 9-10 | Backlog | CHARACTER_SHEET message |

---

## Planned (Not Started)

### Epic 7: Scenario System — Bottle Episodes, Whodunit

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

### Epic 10: NPC Personality — OCEAN Model (P2)

| Feature | Story | Points | Notes |
|---------|-------|--------|-------|
| OCEAN profile fields | 10-1 | 2 | Five floats on NPC |
| Genre archetype baselines | 10-2 | 3 | Default profiles per archetype |
| Behavioral summary | 10-3 | 3 | Scores → prompt text |
| Narrator reads OCEAN | 10-4 | — | Voice/behavior adjustment |
| OCEAN shift log | 10-5 | — | Personality change tracking |
| Agent proposes shifts | 10-6 | — | Event-driven evolution |
| Agreeableness → Disposition | 10-7 | — | Feed into existing system |
| Backfill genre packs | 10-8 | — | Content work |

### Epic 11: Lore & Language — RAG, Conlang Names (P2)

| Feature | Story | Points | Notes |
|---------|-------|--------|-------|
| LoreFragment model | 11-1 | 3 | Indexed narrative facts |
| LoreStore | 11-2 | 3 | In-memory indexed collection |
| Lore seed | 11-3 | 3 | Bootstrap from genre pack |
| Lore in agent prompts | 11-4 | — | Relevant fragment injection |
| Lore accumulation | 11-5 | — | World state writes new fragments |
| Semantic retrieval | 11-6 | — | Embedding-based RAG |
| Morpheme glossary | 11-7 | — | Conlang morphemes |
| Name bank generation | 11-8 | — | Glossed names from language rules |
| Narrator name injection | 11-9 | — | Consistent naming |
| Language as KnownFact | 11-10 | — | Transliteration growth |

---

## Summary

| Category | Stories Done | Stories Total | Completion |
|----------|-------------|---------------|------------|
| Epic 1: Workspace Scaffolding | 13/13 | 13 | 100% |
| Epic 2: Core Game Loop | 9/9 | 9 | 100% |
| Epic 3: Game Watcher | 9/9 | 9 | 100% |
| Epic 4: Media Integration | 12/12 | 12 | 100% |
| Epic 5: Pacing & Drama | 4/10 | 10 | 40% |
| Epic 6: Active World | 3/9 | 9 | 33% |
| Epic 7: Scenario System | 0/9 | 9 | 0% |
| Epic 8: Multiplayer | 8/9 | 9 | 89% |
| Epic 9: Character Depth | 1/10 | 10 | 10% |
| Epic 10: OCEAN Personality | 0/8 | 8 | 0% |
| Epic 11: Lore & Language | 0/10 | 10 | 0% |
| **Total** | **59/108** | **108** | **55%** |

### What's Playtest-Ready Today

The core loop is complete: connect → create character → play → narrate → render images → synthesize voice → play music. Multiplayer works. The GM watcher dashboard is live. All seven genre packs load. The pacing engine is partially wired (tension tracking active, drama-aware delivery not yet).

**Best playtest experience:** Single-player or multiplayer session in any genre pack. Full media pipeline (images, voice, music). Trope engine drives narrative arcs. Combat works with turn management.

**Not yet exercised:** Faction agendas, scenario/mystery mechanics, OCEAN personality, lore retrieval, server-side slash commands, drama-aware text delivery speed.
