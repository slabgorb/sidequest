# SideQuest Feature Inventory

**Last updated:** 2026-04-06
**Sprint 1:** Bootstrap Rust workspace (completed)
**Sprint 2:** Multiplayer Works For Real (active — 975/1095 points, 272/307 stories)

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
| Genre pack loading | sidequest-genre crate | ThemeProvider (CSS vars) | — | 11 packs, validated |
| CORS support | axum middleware | Vite proxy | — | Dev + prod |

### Media Pipeline (Epic 4, complete)

| Feature | API | UI | Daemon | Notes |
|---------|-----|-----|--------|-------|
| Image generation | Subject extractor → Render queue | IMAGE display | Flux.1 (schnell + dev) via MLX | Multiple tiers: scene, portrait, landscape, text, cartography, tactical |
| Beat filter | Suppress low-drama renders | — | — | drama_weight threshold |
| Speculative prerender | Queue against turn boundaries | — | — | Hash-based cache dedup (ADR-044) |
| Music direction | Mood extraction from narration | useAudioCue | Audio library backend | AUDIO_CUE messages → pre-rendered ACE-Step tracks |
| 2-channel audio | Music + SFX commands | AudioStatus component | pygame mixer | No voice/TTS channel after 2026-04 removal |
| Theme rotation | Anti-repetition track selection | — | Audio rotator | Mood-based |
| ~~TTS voice synthesis~~ | **Removed 2026-04** — Kokoro TTS pipeline removed; see ADR-076 | | | |
| ~~Character voice mapping~~ | **Removed 2026-04** alongside TTS | | | |

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

### Sealed Letter Turn System (Epic 13, 7/11 done)

Simultaneous input collection with player visibility.

### Scenario System (Epic 7, 7/10 done)

Bottle episodes, whodunit, belief state — core mechanics wired.

### Dungeon Crawl Engine (Epic 19, 7/10 done)

Room graph navigation & resource pressure.

### Narrator Prompt Architecture (Epic 23, 6/10 done)

Template, RAG, universal cartography.

### Wiring Audit Remediation (Epic 26, 3/9 done)

Unwired modules, protocol gaps, OTEL blind spots.

### Portrait Identity Consistency (Epic 17, 0/6 done)

Tiered character recognition pipeline.

### Seed Tropes (Epic 22, 0/6 done)

Narrative variety via Schrödinger's gun.

### Procedural World-Grounding Systems (Epic 24, 0/9 done)

Server-side pre-generation pipeline.

### Completed This Sprint (archived)

- **Epic 14:** Multiplayer Session UX (10/10)
- **Epic 15:** Playtest Debt Cleanup (32/32)
- **Epic 16:** Genre Mechanics Engine — Confrontations & Resources (17/17)
- **Epic 18:** OTEL Dashboard — Granular Instrumentation (9/9)
- **Epic 20:** Narrator Crunch Separation — Tool-Based Mechanics (14/14)
- **Epic 21:** Claude Subprocess OTEL Passthrough (5/5)
- **Epic 25:** UI Redesign — Character Panel, Layout Modes (11/11)

---

## Planned (Not Started)

---

## Summary

| Category | Done | Total | Completion |
|----------|------|-------|------------|
| Epic 1: Workspace Scaffolding | 15/15 | 15 | 100% |
| Epic 2: Core Game Loop | 10/10 | 10 | 100% |
| Epic 3: Game Watcher | 10/10 | 10 | 100% |
| Epic 4: Media Integration | 13/13 | 13 | 100% |
| Epic 5: Pacing & Drama | 11/11 | 11 | 100% |
| Epic 6: Active World | 10/10 | 10 | 100% |
| Epic 7: Scenario System | 7/10 | 10 | 70% |
| Epic 8: Multiplayer | 10/10 | 10 | 100% |
| Epic 9: Character Depth | 14/14 | 14 | 100% |
| Epic 10: OCEAN Personality | 9/9 | 9 | 100% |
| Epic 11: Lore & Language | 11/11 | 11 | 100% |
| Epic 12: Cinematic Audio | 4/4 | 4 | 100% |
| Epic 13: Sealed Letter Turns | 7/11 | 11 | 64% |
| Epic 14: Session UX | 10/10 | 10 | 100% |
| Epic 15: Playtest Debt | 32/32 | 32 | 100% |
| Epic 16: Genre Mechanics Engine | 17/17 | 17 | 100% |
| Epic 17: Portrait Identity | 0/6 | 6 | 0% |
| Epic 18: OTEL Dashboard | 9/9 | 9 | 100% |
| Epic 19: Dungeon Crawl Engine | 7/10 | 10 | 70% |
| Epic 20: Narrator Crunch Sep. | 14/14 | 14 | 100% |
| Epic 21: Claude OTEL Passthrough | 5/5 | 5 | 100% |
| Epic 22: Seed Tropes | 0/6 | 6 | 0% |
| Epic 23: Narrator Prompt Arch. | 6/10 | 10 | 60% |
| Epic 24: Procedural World | 0/9 | 9 | 0% |
| Epic 25: UI Redesign | 11/11 | 11 | 100% |
| Epic 26: Wiring Audit | 3/9 | 9 | 33% |
| **Total** | **272/307** | **307** | **89%** |

### What's Playtest-Ready Today

The full game loop is wired end-to-end: connect → create character → play → narrate → render images → synthesize voice → play music. Multiplayer works with turn barriers, adaptive batching, and party action composition across all three turn modes. The GM watcher dashboard is live with granular OTEL instrumentation. All 11 genre packs load with OCEAN personality profiles, confrontation engines, and resource tracking.

Narrator crunch separation is complete — mechanical state changes (items, quests, mood, SFX, resource deltas) are handled by sidecar tools during narration, not extracted from prose. The UI has been redesigned with new character panels, layout modes, and chrome.

**Best playtest experience:** Multiplayer session in any genre pack. Full media pipeline. Faction-driven world. OCEAN personality on NPCs. Footnoted narration with journal. Pacing engine shapes delivery speed and narrator length. Confrontation engine with genre-specific resource pools.

**Sprint 2 remaining:** Sealed letter turn polish, scenario system wiring, dungeon crawl engine, narrator prompt architecture, portrait identity pipeline, seed tropes, procedural world grounding, and wiring audit remediation.
