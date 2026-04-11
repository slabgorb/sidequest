# SideQuest — Wiring Diagrams

> End-to-end signal traces for every major feature. Each diagram shows the path from
> visible UI feature through server layers to storage, with file paths and function names.
>
> **Last updated:** 2026-04-06
> **Source of truth:** `sidequest-api/crates/` — traced from actual code, not design docs.

---

## Table of Contents

1. [Core Turn Loop](#1-core-turn-loop) — Action → Narration → State Delta
2. [Narrator Prompt Assembly](#2-narrator-prompt-assembly) — Attention Zones → Tiered Composition → Claude CLI
3. [Image Generation](#3-image-generation) — Narration → Subject → Beat Filter → Daemon → IMAGE
4. [TTS Voice Pipeline (removed)](#4-tts-voice-pipeline-removed) — Retired in Epic 27 / ADR-076
5. [Music & Audio](#5-music--audio) — Narration → Mood → Track Selection → AUDIO_CUE
6. [Multiplayer Turn Barrier](#6-multiplayer-turn-barrier) — Sealed Letter Collection → Resolution
7. [Combat Flow](#7-combat-flow) — State Override → Mutations → COMBAT_EVENT
8. [Character Creation](#8-character-creation) — Builder State Machine → Character
9. [Pacing & Drama Engine](#9-pacing--drama-engine) — TensionTracker → Delivery Mode → Prompt
10. [Knowledge Pipeline](#10-knowledge-pipeline) — Footnotes → KnownFacts → Lore → Prompt
11. [NPC Personality (OCEAN)](#11-npc-personality-ocean) — Profiles → Behavioral Summary → Prompt
12. [Faction Agendas & Scene Directives](#12-faction-agendas--scene-directives) — Agendas → Directives → Narrator
13. [Slash Commands](#13-slash-commands) — /command → Router → Response
14. [Trope Engine](#14-trope-engine) — Tick → Beat Firing → Narrator Injection
15. [Session Persistence](#15-session-persistence) — GameSnapshot → SQLite → Recovery
16. [Genre Pack Loading](#16-genre-pack-loading) — YAML → Typed Structs → Session State

---

## 1. Core Turn Loop

The central pipeline from player input to narrated response.

```mermaid
flowchart TD
    A["Client: PLAYER_ACTION<br/>(WebSocket JSON)"] --> B["ws.rs:169<br/>serde_json::from_str"]
    B --> C["ws.rs:171<br/>dispatch_message()"]
    C --> D["dispatch.rs:331<br/>dispatch_player_action()"]

    D --> E["dispatch.rs:1541<br/>Slash command check"]
    E -->|"/command"| F["slash_router.rs:63<br/>try_dispatch()"]
    F --> Z2["Early return:<br/>NARRATION response"]
    E -->|"normal action"| G["dispatch.rs:2130<br/>preprocess_action()"]

    G --> H["dispatch.rs:1731<br/>Build state_summary<br/>(HP, location, inventory,<br/>NPCs, tropes, lore, axes,<br/>narration history)"]
    H --> I["dispatch.rs:2140<br/>TurnContext creation"]
    I --> J["orchestrator.rs:133<br/>IntentRouter::classify_with_state()"]

    J -->|"state override"| K1["Combat → CreatureSmith"]
    J -->|"state override"| K2["Chase → Dialectician"]
    J -->|"keyword match"| K3["Dialogue → Ensemble"]
    J -->|"default"| K4["Exploration → Narrator"]

    K1 & K2 & K3 & K4 --> L["orchestrator.rs:144<br/>agent.build_context()<br/>+ PromptBuilder.compose()"]
    L --> M["client.rs:195<br/>Command::new('claude')<br/>.arg('-p').arg(prompt)<br/>120s timeout"]
    M --> N["orchestrator.rs:177<br/>extract_structured_from_response()<br/>(footnotes, items, NPCs, quests)"]

    N --> O["dispatch.rs:2178<br/>extract_location_header()"]
    O --> P["dispatch.rs:2263<br/>Update NPC registry"]
    P --> Q["dispatch.rs:2374<br/>Apply combat patches"]
    Q --> R["dispatch.rs:2405<br/>Merge quest updates"]
    R --> S["dispatch.rs:2413<br/>XP + level progression"]
    S --> T["dispatch.rs:2570<br/>Extract items → inventory"]

    T --> U["dispatch.rs:2698<br/>GameMessage::Narration{<br/>text, state_delta, footnotes}"]
    U --> V["dispatch.rs:2741<br/>GameMessage::NarrationEnd"]
    V --> W["+ PARTY_STATUS<br/>+ INVENTORY<br/>+ MAP_UPDATE<br/>+ COMBAT_EVENT<br/>+ CHAPTER_MARKER"]

    W --> X["ws.rs:207<br/>tx.send(resp) → mpsc"]
    X --> Y["ws.rs:51<br/>writer_handle:<br/>rx.recv() → ws_sink.send()"]
    Y --> Z["Client: NARRATION<br/>(WebSocket JSON)"]

    style A fill:#4a9eff,color:#fff
    style Z fill:#4a9eff,color:#fff
    style Z2 fill:#4a9eff,color:#fff
    style M fill:#ff6b6b,color:#fff
```

**Key files:** `ws.rs` → `dispatch.rs` → `orchestrator.rs` → `client.rs` → back through `dispatch.rs`

**Storage touched:** NPC registry, quest log, inventory, XP/level, narration history, lore store

---

## 2. Narrator Prompt Assembly

How the narrator prompt is composed from ~30 sections across 5 attention zones, with Full vs Delta tiering (ADR-066).

```mermaid
flowchart TD
    subgraph TRIGGER["Trigger"]
        A["dispatch_player_action()<br/>(dispatch/mod.rs)"]
    end

    A --> B["IntentRouter::classify_with_state()<br/>(intent_router.rs)<br/>State override — no keyword matching"]
    B --> C{"Game state?"}
    C -->|"in_combat"| C1["Intent::Combat"]
    C -->|"in_chase"| C2["Intent::Chase"]
    C -->|"default"| C3["Intent::Exploration"]

    C1 & C2 & C3 --> D{"First turn<br/>of session?"}
    D -->|"yes"| E["Full Tier<br/>(~15KB system prompt)"]
    D -->|"no"| F["Delta Tier<br/>(dynamic state only)"]

    E & F --> G["ContextBuilder<br/>(context_builder.rs)"]

    subgraph PRIMACY["Primacy Zone — Maximum Attention"]
        P1["narrator_identity<br/>'You are the Game Master…'"]
        P2["narrator_constraints<br/>Silent constraint handling"]
        P3["narrator_agency<br/>PC puppet prevention + multiplayer"]
        P4["narrator_consequences<br/>Genre tone alignment"]
        P5["narrator_output_only ★<br/>Complete game_patch schema<br/>(~150 lines, ALL fields)"]
        P6["genre_identity ★<br/>'You are narrating a {genre} game'"]
    end

    subgraph EARLY["Early Zone — High Attention"]
        E1["narrator_output_style<br/>Formatting rules"]
        E2["narrator_combat_rules ★<br/>Always injected (ADR-067)"]
        E3["narrator_chase_rules<br/>If in_chase"]
        E4["narrator_dialogue_rules ★<br/>Always injected"]
        E5["soul_principles<br/>From SOUL.md (filtered per agent)"]
        E6["trope_beat_directives<br/>MANDATORY scene elements"]
    end

    subgraph VALLEY["Valley Zone — Moderate Attention"]
        V1["game_state ★<br/>HP, inventory, quests,<br/>known facts, tropes,<br/>resources, party roster<br/>(dispatch/prompt.rs)"]
        V2["ocean_personalities<br/>NPC behavioral summaries"]
        V3["ability_context<br/>Character involuntary abilities"]
        V4["world_lore<br/>Graph-filtered by distance<br/>(lore_filter.rs)"]
        V5["merchant_context<br/>Available merchants + inventory"]
        V6["world_context<br/>History chapters by maturity"]
        V7["genre_resources<br/>Current/max, decay rates"]
        V8["sfx_library<br/>Available SFX IDs"]
    end

    subgraph LATE["Late Zone — Lower Attention"]
        L1["narrator_vocabulary<br/>Accessible / Literary / Epic"]
        L2["footnote_protocol<br/>Knowledge extraction rules"]
        L3["backstory_capture<br/>If intent == Backstory"]
    end

    subgraph RECENCY["Recency Zone — Highest Attention"]
        R1["narrator_verbosity ★<br/>Length limits in chars"]
        R2["opening_scene_constraint<br/>First-turn length cap"]
        R3["player_action ★<br/>'{character} says: {action}'"]
    end

    G --> PRIMACY --> EARLY --> VALLEY --> LATE --> RECENCY

    RECENCY --> H{"Tier?"}
    H -->|"Full"| I["claude --model opus<br/>--session-id {UUID}<br/>--system-prompt {zones}<br/>-p {action}"]
    H -->|"Delta"| J["claude --model opus<br/>--resume {session_id}<br/>-p {zones + action}"]

    I & J --> K["Parse JSON response"]
    K --> L["Extract:<br/>narration, game_patch,<br/>combat_patch, chase_patch,<br/>footnotes, items, NPCs,<br/>visual_scene, sfx_triggers,<br/>personality_events"]
    L --> M["ActionResult<br/>→ back to dispatch"]

    style A fill:#6c5ce7,color:#fff
    style M fill:#6c5ce7,color:#fff
    style I fill:#ff6b6b,color:#fff
    style J fill:#ff6b6b,color:#fff
    style PRIMACY fill:#ff634720,stroke:#ff6347
    style EARLY fill:#ffa50020,stroke:#ffa500
    style VALLEY fill:#32cd3220,stroke:#32cd32
    style LATE fill:#4169e120,stroke:#4169e1
    style RECENCY fill:#9370db20,stroke:#9370db
```

**★ = injected on EVERY tier** (Full and Delta). Unmarked = Full tier only or conditional.

**Attention zone ordering:** Primacy (0) → Early (1) → Valley (2) → Late (3) → Recency (4). Sections added in any order; `compose()` sorts by zone before joining.

**Delta tier key rule:** `narrator_output_only` (complete game_patch schema) is re-sent every turn — without it, the LLM stops emitting structured JSON.

**Token telemetry:** Per-zone token estimates emitted via OTEL for the Prompt Inspector dashboard.

---

## 3. Image Generation

Background pipeline — narration triggers render, result arrives asynchronously via RENDER_QUEUED → IMAGE replacement.

```mermaid
flowchart TD
    A["ActionResult from narrator"] --> B{"visual_scene<br/>in game_patch?"}
    B -->|"yes"| C["Use narrator's visual_scene<br/>(tier, subject, mood, tags)"]
    B -->|"no"| D["SubjectExtractor::extract()<br/>(subject.rs)<br/>Regex fallback from narration"]
    C & D --> E{"RenderSubject?"}
    E -->|"None"| Z1["No image this turn"]
    E -->|"Some(subject)"| F["SceneRelevanceValidator<br/>(render.rs)<br/>Reject mismatched context"]

    F --> G{"Valid?"}
    G -->|"rejected"| Z3["OTEL: relevance_rejected"]
    G -->|"valid"| H["BeatFilter::evaluate()<br/>(beat_filter.rs)"]

    H --> I{"FilterDecision"}
    I -->|"Suppress"| Z2["Filtered: low weight,<br/>cooldown, or burst rate"]
    I -->|"Render"| J["RenderQueue::enqueue()<br/>SHA256 content dedup"]

    J --> K["RENDER_QUEUED broadcast<br/>(render_id, tier, dimensions)"]
    K --> K2["Client: shimmer placeholder"]

    J --> L["Visual style lookup<br/>(visual_style.yaml)<br/>positive_suffix, negative_prompt,<br/>LoRA path, seed"]
    L --> M["DaemonClient::render()<br/>Unix socket → /tmp/sidequest-renderer.sock<br/>RenderParams (300s timeout)"]

    M --> N["sidequest-daemon (Python)"]

    subgraph DAEMON["Daemon Pipeline"]
        N1["PromptComposer<br/>Tier prefix + subject + style<br/>T5 (512 tok) + CLIP (77 tok)<br/>+ negative prompt"]
        N2["FluxWorker<br/>Flux.1-dev (12 steps) or<br/>Flux.1-schnell (4 steps)"]
        N3["Optional: LoRA adapter<br/>(ADR-032)"]
        N4["Optional: IP-Adapter<br/>reference portrait (ADR-034)"]
        N1 --> N2
        N3 -.-> N2
        N4 -.-> N2
    end
    N --> N1

    N2 --> O["RenderResult<br/>{image_url, generation_ms}"]

    O --> P["Image Broadcaster<br/>(render_integration.rs)<br/>Pacing throttle: 30s solo, 60s multi"]
    P --> Q{"image_url<br/>empty?"}
    Q -->|"yes"| Z4["Reject — no silent fallback"]
    Q -->|"no"| R["GameMessage::Image<br/>{url, description, tier,<br/>scene_type, handout, render_id}"]

    R --> S["Client: replace shimmer<br/>with actual image<br/>(match by render_id)"]

    style A fill:#6c5ce7,color:#fff
    style S fill:#4a9eff,color:#fff
    style K2 fill:#4a9eff,color:#fff
    style N2 fill:#00b894,color:#fff
```

**Subject extraction:** Narrator's `visual_scene` (from game_patch) is preferred; regex `SubjectExtractor` is fallback only.

**Beat filter gates:** narrative weight (>0.4), cooldown (2-4 turns), burst rate (max 2/turn), SHA256 dedup.

**Render tiers:** portrait (768×1024), landscape (1024×768), scene_illustration (768×768), tactical_sketch (1024×1024), cartography (1024×1024), text_overlay (768×512).

**Handout classification:** Discovery scenes and dialogue portraits flagged as `handout: true` → persisted in player journal.

---

## 4. TTS Voice Pipeline (removed)

The Kokoro TTS streaming pipeline was retired in **Epic 27 (MLX Image Renderer)**
when the sidequest-daemon was narrowed to a single-purpose Flux image renderer.
The follow-up protocol cleanup landed in **ADR-076 / story 27-9**, which removed
the `GameMessage::NarrationChunk` variant and `NarrationChunkPayload` struct
from the protocol crate, and the corresponding UI narration buffer that was
designed to synchronize text reveal with incoming PCM voice frames.

Current narration delivery is the simplified two-message flow shown in
[Section 1 — Core Turn Loop](#1-core-turn-loop):

```
GameMessage::Narration { text, state_delta, footnotes }
GameMessage::NarrationEnd { state_delta }
```

The UI pairs `Narration` with its terminal `NarrationEnd` in a small buffer so
any end-of-turn `state_delta` applies in the same React commit as the narration
text. There is no longer any streaming-chunks leg, no binary voice frames, and
no audio ducking around speech.

If TTS is reintroduced later, it will almost certainly use a different
streaming shape (e.g. a single `VoiceTrack` message with a URL reference, or
post-narration audio job queued like images are). See ADR-076 Alternatives
Considered for the rationale.

---

## 5. Music & Audio

Mood classification drives track selection with anti-repetition rotation.

```mermaid
flowchart TD
    A["Narration text"] --> B["dispatch.rs:3209<br/>MusicDirector::classify_mood()<br/>(music_director.rs:145)"]

    B --> C["MoodContext:<br/>in_combat, in_chase,<br/>party_health_pct,<br/>quest_completed, npc_died"]
    C --> D["MoodClassification:<br/>{primary: Mood, intensity, confidence}"]

    D --> E["MusicDirector::evaluate()<br/>(music_director.rs:156)"]
    E --> F["Look up mood_tracks<br/>from genre pack AudioConfig"]
    F --> G["ThemeRotator::select()<br/>(theme_rotator.rs:68)"]

    G --> H{"Anti-repetition<br/>filter"}
    H -->|"all exhausted"| I["Reset history"]
    H -->|"candidates remain"| J["Score by<br/>energy-to-intensity<br/>distance"]
    I --> J
    J --> K["Top candidate<br/>(randomize from top 3)"]

    K --> L["AudioMixer::apply_cue()<br/>(audio_mixer.rs)"]
    L --> M["dispatch.rs:3822<br/>audio_cue_to_game_message()"]
    M --> N["GameMessage::AudioCue<br/>{mood, music_track,<br/>channel, action, volume}"]
    N --> O["Client: AUDIO_CUE"]

    style A fill:#6c5ce7,color:#fff
    style O fill:#4a9eff,color:#fff
```

**Moods:** Combat, Exploration, Tension, Triumph, Sorrow, Mystery, Calm

**Variation selection (6-tier priority):** Overture (session start/location change) → Resolution (combat ended/quest completed) → TensionBuild (intensity ≥0.7 or drama ≥0.7) → Ambient (intensity ≤0.3 or scene turn ≥4) → Sparse (mid-intensity, low drama) → Full (fallback)

**MoodContext inputs:** in_combat, in_chase, party_health_pct, quest_completed, npc_died, encounter_mood_override, location_changed, scene_turn_count, drama_weight (from TensionTracker)

**3 channels:** music, sfx, ambience — each with independent volume and action (play/fade_in/fade_out/duck/restore/stop). Default volumes: music 0.7, sfx 0.8, voice 1.0, ambience 0.3.

**Rotation depth:** 3 tracks per mood before repeat allowed

**Client (useAudioCue.ts):** Routes AUDIO_CUE by action field — configure/duck/restore/fade_out/play. AudioEngine handles crossfade between tracks, AudioCache prevents re-decoding.

---

## 6. Multiplayer Turn Barrier

Sealed letter pattern — all players submit, one handler resolves.

```mermaid
flowchart TD
    A["Player A: PLAYER_ACTION"] --> B["dispatch.rs:2039<br/>turn_mode.should_use_barrier()?"]
    A2["Player B: PLAYER_ACTION"] --> B2["dispatch.rs:2039<br/>should_use_barrier()?"]

    B -->|"Structured/Cinematic"| C["barrier.rs:255<br/>submit_action(player_a, action_a)"]
    B2 -->|"Structured/Cinematic"| C2["barrier.rs:255<br/>submit_action(player_b, action_b)"]

    C --> D["multiplayer.rs:292<br/>record_action() → HashMap"]
    C2 --> D

    D --> E["multiplayer.rs:305<br/>is_barrier_met()?<br/>actions.len() >= players.len()"]
    E -->|"yes"| F["inner.notify.notify_one()"]
    E -->|"no, wait"| G["barrier.rs:303<br/>wait_for_turn()<br/>tokio::select!{<br/>  notify.notified(),<br/>  sleep(adaptive_timeout)<br/>}"]

    G -->|"timeout"| H["barrier.rs:342<br/>force_resolve_turn()<br/>'hesitates, waiting'"]
    F --> I["barrier.rs:329<br/>resolution_lock.lock()"]
    H --> I

    I --> J["barrier.rs:365<br/>try_claim_resolution()"]
    J -->|"true (first caller)"| K["Elected handler:<br/>Gets combined actions<br/>Calls narrator with<br/>PARTY ACTIONS block"]
    J -->|"false (others)"| L["Non-elected:<br/>Receives narration<br/>via session broadcast"]

    K --> M["dispatch.rs:2698<br/>Narrator result"]
    M --> N["dispatch.rs:3661<br/>Broadcast to co-located players"]
    N --> O["Per-player perception filter<br/>(if effects active)"]
    O --> P["All players: NARRATION"]

    M --> Q["dispatch.rs:3717<br/>TURN_STATUS 'resolved'<br/>(global broadcast)"]

    style A fill:#4a9eff,color:#fff
    style A2 fill:#4a9eff,color:#fff
    style P fill:#4a9eff,color:#fff
```

**Adaptive timeout:** 3s for 2-3 players, 5s for 4+ (configurable tiers)

**Resolution lock:** `Mutex` ensures exactly one tokio task calls the narrator — others receive broadcast

**Perception filter:** If a player has perceptual effects, their narration copy is prefixed with `[Your perception is altered: ...]`

---

## 7. Combat Flow

State-override detection (ADR-067, no keyword matching), structured mutations, and CombatOverlay broadcast.

```mermaid
flowchart TD
    A["Player action"] --> B["IntentRouter::classify_with_state()<br/>(intent_router.rs)<br/>ADR-067: state override only"]
    B --> C{"in_combat == true?"}
    C -->|"yes"| D["Intent::Combat<br/>source: StateOverride<br/>confidence: 1.0"]
    C -->|"no"| E["Intent::Exploration<br/>(or Chase if in_chase)"]

    D --> F["Narrator agent responds<br/>with combat_patch in game_patch"]
    E --> F

    F --> G["apply_state_mutations()<br/>(state_mutations.rs)"]

    G --> H{"combat_patch<br/>.in_combat?"}
    H -->|"Some(true) &<br/>!was_in_combat"| I["CombatState::engage()<br/>Build turn order<br/>Register combatants in NPC registry<br/>TurnMode: FreePlay → Structured<br/>Activate turn barrier (multiplayer)"]
    H -->|"Some(false) &<br/>was_in_combat"| J["CombatState::disengage()<br/>Clear turn order, reset rounds<br/>TurnMode: Structured → FreePlay"]
    H -->|"None / no change"| K["Continue in current state"]

    G --> L["Apply HP changes"]
    L --> L1{"Target == player?"}
    L1 -->|"yes"| L2["clamp_hp(hp, delta, max_hp)<br/>OTEL: hp_change"]
    L1 -->|"no"| L3["npc_registry[target].hp += delta"]

    I & J & K --> M["process_combat_and_chase()<br/>(dispatch/combat.rs)"]
    L2 & L3 --> M

    M --> N["Tick status effects<br/>(decay durations)"]
    N --> O["Build enemies list<br/>from turn_order + NPC registry<br/>(skip player character)"]
    O --> P["CombatEnemy per NPC:<br/>{name, hp, max_hp, ac,<br/>status_effects[]}"]

    P --> Q["GameMessage::CombatEvent<br/>{in_combat, enemies,<br/>turn_order, current_turn}"]
    Q --> R["WebSocket broadcast"]

    R --> S["App.tsx: setCombatState()"]
    S --> T["CombatOverlay renders:<br/>Turn order (current highlighted)<br/>Enemy HP bars (color-coded)<br/>Status effects + remaining rounds<br/>Fixed top-right, z-index 30"]

    style A fill:#4a9eff,color:#fff
    style T fill:#4a9eff,color:#fff
    style F fill:#ff6b6b,color:#fff
```

**No keyword matching** — combat detection is purely state-driven (ADR-067). `in_combat` flag in game state triggers Intent::Combat.

**Turn mode FSM:** `FreePlay` ↔ `Structured` (on combat start/end), `FreePlay` → `Cinematic` (on cutscene)

**CombatState tracks:** round counter, turn_order, current_turn, damage log, status effects (Poison/Stun/Bless/Curse with duration decay), drama_weight, available_actions

**HP bar colors:** green (>50%), orange (25-50%), red (<25%). Status indicators: "bloodied" at 50%, "defeated" at 0 HP.

**Status effect colors:** Poison (green), Stun (yellow), Bless (blue), Curse (purple)

---

## 8. Character Creation

Genre-driven scene-based state machine with bidirectional messages.

```mermaid
flowchart TD
    A["SESSION_EVENT{connect}<br/>genre, world, player_name"] --> B["dispatch.rs:439<br/>persistence.exists()?"]
    B -->|"returning"| C["Load GameSnapshot<br/>→ skip creation<br/>→ Playing state"]
    B -->|"new"| D["SESSION_EVENT{connected,<br/>has_character: false}"]

    D --> E["builder.rs<br/>CharacterBuilder::try_new()<br/>(genre scenes + rules)"]
    E --> F["builder.to_scene_message()<br/>→ CHARACTER_CREATION<br/>{phase: 'scene', scene_index,<br/>choices, allows_freeform}"]

    F --> G["Client: show scene"]
    G --> H["Client: CHARACTER_CREATION<br/>{phase: 'scene', choice}"]
    H --> I["dispatch.rs:983<br/>builder.apply_choice(index)"]
    I --> J{"More scenes?"}
    J -->|"yes"| F
    J -->|"no"| K["CHARACTER_CREATION<br/>{phase: 'confirmation',<br/>character_preview}"]

    K --> L["Client: confirm"]
    L --> M["dispatch.rs:996<br/>builder.build(player_name)"]
    M --> N["AccumulatedChoices →<br/>Character with CreatureCore<br/>(HP, AC, abilities, inventory)"]
    N --> O["CHARACTER_CREATION<br/>{phase: 'complete', character}"]
    O --> P["Session → Playing state"]
    P --> Q["LoreStore seeded from<br/>creation choices (story 11-3)"]

    style A fill:#4a9eff,color:#fff
    style G fill:#4a9eff,color:#fff
    style L fill:#4a9eff,color:#fff
```

**Accumulated from scenes:** class, race, personality, items, affinity, backstory fragments, stat bonuses, pronouns, rig type, catch phrase

**3 creation modes (ADR-016):** Menu (pick from list), Guided (follow prompts), Freeform (describe anything)

---

## 9. Pacing & Drama Engine

Dual-track tension model drives narration length and delivery speed.

```mermaid
flowchart TD
    A["Each turn: combat events,<br/>HP changes, action results"] --> B["tension_tracker.rs:397<br/>TensionTracker::observe()"]
    B --> C["Classify: Boring/Dramatic/Normal"]
    C --> D["Update action_tension<br/>(gambler's ramp)"]
    D --> E["Inject event spikes<br/>(critical hit, death save)"]

    F["Each turn"] --> G["tension_tracker.rs:209<br/>TensionTracker::tick()"]
    G --> H["action_tension *= 0.9<br/>(ACTION_DECAY)"]
    H --> I["Age existing spikes<br/>(linear decay)"]

    I --> J["tension_tracker.rs:137<br/>drama_weight =<br/>max(action, stakes, spike)"]
    J --> K["tension_tracker.rs:214<br/>pacing_hint()"]

    K --> L{"drama_weight<br/>thresholds"}
    L -->|"> streaming_min"| M["DeliveryMode::Streaming<br/>(word-by-word)"]
    L -->|">= sentence_min"| N["DeliveryMode::Sentence<br/>(sentence-by-sentence)"]
    L -->|"< sentence_min"| O["DeliveryMode::Instant<br/>(full text)"]

    K --> P["PacingHint::<br/>narrator_directive()"]
    P --> Q["'Target N sentences.<br/>Drama level: X%.'"]

    K --> R{"boring_streak >=<br/>escalation_streak?"}
    R -->|"yes"| S["Inject escalation beat"]
    R -->|"no"| T["No escalation"]

    Q --> U["prompt_framework/mod.rs:82<br/>register_pacing_section()<br/>Late attention zone"]
    S --> U
    U --> V["Narrator prompt<br/>(length + urgency guidance)"]

    style V fill:#ff6b6b,color:#fff
```

**Genre-tunable:** `pacing.yaml` in genre pack sets `streaming_delivery_min`, `sentence_delivery_min`, `escalation_streak`

**Dual tracks:** Action tension (gambler's ramp from boring streaks) + Stakes tension (HP ratio) + Event spikes (discrete dramatic moments)

---

## 10. Knowledge Pipeline

Narrator footnotes become persistent facts that feed back into future prompts.

```mermaid
flowchart TD
    A["Narrator response:<br/>prose + JSON block"] --> B["orchestrator.rs:325<br/>extract_structured_from_response()"]
    B --> C["footnotes: Vec&lt;Footnote&gt;<br/>{marker, summary, category,<br/>is_new, fact_id}"]

    C --> D["dispatch.rs:2698<br/>Attach to NarrationPayload<br/>(sent to client)"]
    D --> E["Client: render [N] superscripts<br/>+ footnote entries below narration"]

    C --> F["dispatch.rs:2723<br/>footnotes_to_discovered_facts()<br/>(footnotes.rs:20)"]
    F --> G{"is_new?"}
    G -->|"true"| H["Create DiscoveredFact<br/>{content, category, turn,<br/>source: Discovery,<br/>confidence: Certain}"]
    G -->|"false"| I["Callback to existing<br/>KnownFact via fact_id"]

    H --> J["Character.known_facts<br/>accumulation"]
    J --> K["Next turn:<br/>prompt_framework/mod.rs:173<br/>register_knowledge_section()"]
    K --> L["[CHARACTER's KNOWLEDGE]<br/>Top 20 facts by recency<br/>with confidence tags<br/>Valley attention zone"]
    L --> M["Narrator prompt<br/>(don't-repeat constraint)"]

    H --> N["lore.rs:430<br/>accumulate_lore()<br/>→ LoreStore"]
    N --> O["lore.rs:354<br/>select_lore_for_prompt()<br/>(budget-aware, keyword-hinted)"]
    O --> P["Narrator/agent prompts<br/>(grounding zone)"]

    style A fill:#6c5ce7,color:#fff
    style E fill:#4a9eff,color:#fff
    style M fill:#ff6b6b,color:#fff
    style P fill:#ff6b6b,color:#fff
```

**FactCategory:** Lore, Place, Person, Quest, Ability

**Lore budget:** Token-aware selection prevents prompt bloat (content.len / 4 token estimate)

**Feedback loop:** Footnotes → KnownFacts → prompt injection → narrator avoids repeating → new footnotes

---

## 11. NPC Personality (OCEAN)

Big Five profiles loaded from genre packs, summarized into narrator prompts.

```mermaid
flowchart TD
    A["Genre pack YAML<br/>archetypes.yaml"] --> B["GenreLoader<br/>(sidequest-genre)"]
    B --> C["NPC struct<br/>ocean: Option&lt;OceanProfile&gt;"]

    C --> D["models.rs:119<br/>OceanProfile::behavioral_summary()"]
    D --> E{"Score thresholds"}
    E -->|"<= 3.0"| F["Low descriptor<br/>(e.g., 'reserved', 'blunt')"]
    E -->|">= 7.0"| G["High descriptor<br/>(e.g., 'gregarious', 'meticulous')"]
    E -->|"3.1 - 6.9"| H["Omitted (neutral)"]

    F & G --> I["Joined string:<br/>'reserved and meticulous,<br/>curious and imaginative'"]
    H --> J["Fallback:<br/>'balanced temperament'"]

    I --> K["prompt_framework/mod.rs:109<br/>register_ocean_personalities_section()"]
    J --> K
    K --> L["## NPC Personalities<br/>- Grimjaw: cautious and stubborn<br/>- Lyra: gregarious and creative<br/>Valley attention zone"]
    L --> M["Narrator prompt"]

    C --> N["ocean_shift_proposals.rs<br/>propose_ocean_shifts()<br/>(IMPLEMENTED but NOT WIRED<br/>to game flow — story 15-2)"]
    N -.->|"future"| O["Post-narration pipeline:<br/>detect PersonalityEvents →<br/>apply shifts → log"]

    style A fill:#fdcb6e,color:#333
    style M fill:#ff6b6b,color:#fff
    style N fill:#b2bec3,color:#333
```

**5 dimensions:** Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism (0.0-10.0)

**Agreeableness → Disposition:** A-dimension feeds the existing -15 to +15 disposition system

**Gap:** OCEAN shift proposals are implemented but not wired into the game flow (Epic 15, story 15-2)

---

## 12. Faction Agendas & Scene Directives

Factions pursue goals that inject into every narrator turn.

```mermaid
flowchart TD
    A["Genre pack world YAML<br/>factions section"] --> B["faction_agenda.rs:71<br/>FactionAgenda::try_new()"]
    B --> C["FactionAgenda<br/>{faction_name, goal,<br/>urgency, event_text}"]

    C --> D{"urgency"}
    D -->|"Dormant"| E["Filtered out"]
    D -->|"Simmering/Pressing/Critical"| F["scene_directive.rs:123<br/>agenda.scene_injection()"]

    F --> G["scene_directive.rs:94<br/>format_scene_directive()"]

    H["Trope engine:<br/>fired_beats"] --> G
    I["Active stakes"] --> G

    G --> J["SceneDirective<br/>{trope_beats, faction_events,<br/>active_stakes, hints}"]
    J --> K["prompt_framework/mod.rs:148<br/>register_scene_directive()"]
    K --> L["render_scene_directive()<br/>(mod.rs:26)"]
    L --> M["[SCENE DIRECTIVES — MANDATORY]<br/>Priority-sorted elements:<br/>- TropeBeat instructions<br/>- FactionEvent injections<br/>- ActiveStake markers<br/>Early attention zone"]
    M --> N["Narrator prompt<br/>(high priority, after identity)"]

    style A fill:#fdcb6e,color:#333
    style N fill:#ff6b6b,color:#fff
```

**Urgency levels:** Dormant (filtered), Simmering, Pressing, Critical

**Mandatory weave:** Scene directives use EARLY attention zone — narrator must incorporate them

---

## 13. Slash Commands

Server-side interception before intent classification.

```mermaid
flowchart TD
    A["PLAYER_ACTION<br/>{action: '/status'}"] --> B["dispatch.rs:1541<br/>slash_router check"]
    B --> C["slash_router.rs:63<br/>try_dispatch(input, state)"]
    C --> D{"starts with '/'?"}
    D -->|"no"| E["Pass through to<br/>intent classification"]
    D -->|"yes"| F["Parse: command + args"]

    F --> G{"command"}
    G --> H["/status → StatusCommand<br/>(commands.rs:11)"]
    G --> I["/inventory → InventoryCommand<br/>(commands.rs:44)"]
    G --> J["/map → MapCommand"]
    G --> K["/save → SaveCommand"]
    G --> L["/help → Built-in list"]
    G --> M["/tone → ToneChange"]
    G --> N["/gm → GM suite<br/>(set, teleport, spawn, dmg)"]

    H --> O["CommandResult::Display(text)"]
    I --> P["CommandResult::Display(text)"]
    N --> Q["CommandResult::StateMutation(patch)"]
    M --> R["CommandResult::ToneChange(axes)"]

    O --> S["NARRATION response<br/>(early return)"]
    P --> T["INVENTORY response"]
    Q --> U["Apply patch + NARRATION"]
    R --> V["Update axis_values + NARRATION"]

    style A fill:#4a9eff,color:#fff
    style S fill:#4a9eff,color:#fff
    style T fill:#4a9eff,color:#fff
    style U fill:#4a9eff,color:#fff
    style V fill:#4a9eff,color:#fff
```

**No LLM call:** Slash commands resolve mechanically — no Claude subprocess, no intent classification

**GM commands:** Protected by role check, allow direct state manipulation for debugging

---

## 14. Trope Engine

Genre-defined narrative pacing via trope lifecycle and beat injection.

```mermaid
flowchart TD
    A["Genre pack tropes.yaml<br/>+ world overrides"] --> B["TropeDefinition<br/>{id, name, beats at thresholds,<br/>stakes, NPCs, themes}"]
    B --> C["Session init:<br/>TropeState per definition<br/>(progression: 0.0)"]

    D["Each turn"] --> E["Passive tick:<br/>progression += genre_rate"]
    E --> F{"progression crosses<br/>beat threshold?"}
    F -->|"yes"| G["Fire beat:<br/>FiredBeat{name, event,<br/>stakes, npcs, hints}"]
    F -->|"no"| H["No beat this turn"]

    G --> I["troper.rs:132<br/>build_beats_context()"]
    I --> J["[TROPE BEATS — MANDATORY WEAVE]<br/>Per beat:<br/>  TROPE: name + threshold%<br/>  BEAT EVENT: instruction<br/>  STAKES: what's at risk<br/>  NPCS INVOLVED: list<br/>  NARRATIVE HINTS: enriched<br/>Early attention zone"]

    K["Active tropes (progressing)"] --> L["troper.rs:174<br/>active trope summary"]
    L --> M["Background context on<br/>progressing narrative arcs"]

    J --> N["Narrator prompt"]
    M --> N

    G --> O["scene_directive.rs:94<br/>Also injected into<br/>SceneDirective.trope_beats"]

    style A fill:#fdcb6e,color:#333
    style N fill:#ff6b6b,color:#fff
```

**Trope lifecycle:** Progression 0.0 → 1.0 with beats firing at defined thresholds

**Engagement multiplier:** Scale progression rate by player engagement (turns_since_meaningful)

---

## 15. Session Persistence

Atomic save after every turn, full recovery on reconnect.

```mermaid
flowchart TD
    A["Turn completes"] --> B["dispatch.rs:3273<br/>Build GameSnapshot<br/>(all session state)"]
    B --> C["dispatch.rs:3308<br/>persistence.save()"]
    C --> D["PersistenceHandle<br/>(async wrapper)"]
    D --> E["oneshot channel →<br/>PersistenceWorker<br/>(dedicated OS thread)"]

    E --> F["persistence.rs:242<br/>SqliteStore::save()"]
    F --> G["serde_json::to_string<br/>(full GameSnapshot)"]
    G --> H["rusqlite transaction:<br/>INSERT OR REPLACE<br/>game_state(snapshot_json)"]

    I["Narration text"] --> J["persistence.rs:288<br/>append_narrative()"]
    J --> K["INSERT narrative_log<br/>(round, author, content, tags)"]

    L["Client reconnects<br/>SESSION_EVENT{connect}"] --> M["dispatch.rs:439<br/>persistence.exists()?"]
    M -->|"true"| N["persistence.rs:261<br/>SqliteStore::load()"]
    N --> O["SELECT snapshot_json<br/>FROM game_state"]
    O --> P["serde_json::from_str<br/>→ GameSnapshot"]
    P --> Q["Restore all session state:<br/>character, location, quests,<br/>NPCs, tropes, inventory,<br/>axis values, lore"]
    Q --> R["persistence.rs:284<br/>Generate recap from<br/>recent narrative_log entries"]
    R --> S["SESSION_EVENT{ready}<br/>with initial_state + recap"]

    style A fill:#6c5ce7,color:#fff
    style L fill:#4a9eff,color:#fff
    style S fill:#4a9eff,color:#fff
    style H fill:#e17055,color:#fff
    style K fill:#e17055,color:#fff
```

**Schema:** 3 tables — `session_meta`, `game_state` (single row, full JSON), `narrative_log` (append-only)

**Actor pattern:** `rusqlite::Connection` is `!Send` — wrapped in dedicated OS thread with mpsc command channel

**One DB per session:** `{save_dir}/{genre}/{world}/{player}/save.db`

**GameSnapshot includes:** characters, NPCs, combat, chase, tropes (full TropeState), quests, lore, axis values, achievements, campaign maturity, world history, NPC registry

---

## 16. Genre Pack Loading

Lazy binding — packs loaded per-session on connect, not at startup.

```mermaid
flowchart TD
    A["Server starts<br/>main.rs:36<br/>genre_packs_path from CLI"] --> B["AppState stores path<br/>(no eager loading)"]

    C["Player connects<br/>SESSION_EVENT{connect}<br/>{genre: 'mutant_wasteland',<br/>world: 'flickering_reach'}"] --> D["dispatch.rs:355<br/>GenreLoader::load(genre_slug)"]

    D --> E["loader.rs:19<br/>load_genre_pack(path)"]
    E --> F["Read YAML files:"]
    F --> G["pack.yaml → PackMeta"]
    F --> H["rules.yaml → RulesConfig"]
    F --> I["lore.yaml → Lore"]
    F --> J["archetypes.yaml → NpcArchetypes"]
    F --> K["char_creation.yaml → Scenes"]
    F --> L["visual_style.yaml → VisualStyle"]
    F --> M["audio.yaml → AudioConfig"]
    F --> N["axes.yaml → AxesConfig"]
    F --> O["tropes.yaml → TropeDefinitions"]
    F --> P["cultures.yaml, pacing.yaml,<br/>voice_presets.yaml, etc."]
    F --> Q["worlds/ → World per slug"]

    E --> R["GenrePack (fully typed)"]

    R --> S["Initialize session state:"]
    S --> T["axes_config ← pack.axes"]
    S --> U["trope_defs ← pack.tropes + world overrides"]
    S --> V["visual_style ← pack + world overrides"]
    S --> W["music_director ← pack.audio"]
    S --> X["lore_store ← seeded from pack.lore"]
    S --> Y["voice_router ← pack.voice_presets"]
    S --> Z["beat_filter ← pack.pacing thresholds"]

    style C fill:#4a9eff,color:#fff
    style R fill:#fdcb6e,color:#333
```

**15+ YAML files** per genre pack, all deserialized into typed Rust structs via serde_yaml

**World inheritance:** World-level overrides merge with genre-level defaults (tropes, visual style)

**Lazy binding (ADR-004):** Server starts genre-agnostic; genre bound at runtime on player connect

---

## Color Legend

```
Blue   (#4a9eff)  — Client/WebSocket messages (visible to player)
Purple (#6c5ce7)  — Internal data (narration text, results)
Red    (#ff6b6b)  — Claude CLI subprocess / narrator prompt
Green  (#00b894)  — Python daemon (Flux image gen)
Orange (#e17055)  — SQLite persistence
Yellow (#fdcb6e)  — YAML configuration (genre packs)
Gray   (#b2bec3)  — Not yet wired / stub
```
