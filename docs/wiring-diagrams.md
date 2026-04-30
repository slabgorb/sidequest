# SideQuest — Wiring Diagrams

> End-to-end signal traces for every major feature. Each diagram shows the path
> from visible UI feature through server layers to storage, with module paths and
> function names.
>
> **Last updated:** 2026-04-30
> **Source of truth:** `sidequest-server/sidequest/` (Python tree, post-port per ADR-082).
> The pre-port Rust archive (`sidequest-api`) is read-only at
> <https://github.com/slabgorb/sidequest-api>; some diagrams below describe a
> subsystem that has not yet been re-wired in Python — those are flagged with
> a ⚠️ **port-drift** banner and a pointer to the ADR-087 verdict.

---

## Table of Contents

1. [Core Turn Loop](#1-core-turn-loop) — Action → Narration → State Delta
2. [Narrator Prompt Assembly](#2-narrator-prompt-assembly) — Attention Zones → Tiered Composition → Claude CLI
3. [Image Generation](#3-image-generation) — Narration → Subject → Drama Gate → Daemon → IMAGE
4. [TTS Voice Pipeline (removed)](#4-tts-voice-pipeline-removed) — Retired in Epic 27 / ADR-076
5. [Music & Audio](#5-music--audio) — Narration → Mood → Track Selection → AUDIO_CUE
6. [Multiplayer Turn Barrier](#6-multiplayer-turn-barrier) — Sealed Letter Collection → Resolution
7. [Combat & Encounter Flow](#7-combat--encounter-flow) — State Override → Mutations → COMBAT_EVENT
8. [Character Creation](#8-character-creation) — Builder State Machine → Character
9. [Pacing & Drama Engine](#9-pacing--drama-engine) — TensionTracker → Delivery Mode → Prompt
10. [Knowledge Pipeline](#10-knowledge-pipeline) — Footnotes → KnownFacts → Lore → Prompt
11. [NPC Personality (OCEAN)](#11-npc-personality-ocean) — Profiles → Behavioral Summary → Prompt
12. [Faction Agendas & Scene Directives](#12-faction-agendas--scene-directives) — Agendas → Directives → Narrator
13. [Slash Commands](#13-slash-commands) — /command → Router → Response
14. [Trope Engine](#14-trope-engine) — Tick → Beat Firing → Narrator Injection ⚠️ **partial**
15. [Session Persistence](#15-session-persistence) — GameSnapshot → SQLite → Recovery
16. [Genre Pack Loading](#16-genre-pack-loading) — YAML → Pydantic → Session State

---

## 1. Core Turn Loop

The central pipeline from player input to narrated response. All paths are Python modules under `sidequest-server/sidequest/`.

```mermaid
flowchart TD
    A["Client: PLAYER_ACTION<br/>(WebSocket JSON)"] --> B["server/websocket.py<br/>pydantic discriminated union<br/>parses GameMessage"]
    B --> C["server/session_handler.py<br/>dispatch_message()"]
    C --> D["server/session_handler.py<br/>dispatch_player_action()"]

    D --> E["Slash command check"]
    E -->|"/command"| F["game/commands.py<br/>try_dispatch()"]
    F --> Z2["Early return:<br/>NARRATION response"]
    E -->|"normal action"| G["preprocess_action()"]

    G --> H["Build state_summary<br/>(HP, location, inventory,<br/>NPCs, tropes, lore, axes,<br/>narration history)"]
    H --> I["TurnContext"]
    I --> J["agents/orchestrator.py<br/>IntentRouter.classify_with_state()"]

    J -->|"state override"| K1["Combat → unified narrator"]
    J -->|"state override"| K2["Chase → unified narrator"]
    J -->|"default"| K3["Exploration → unified narrator"]

    K1 & K2 & K3 --> L["agents/orchestrator.py<br/>narrator.build_context()<br/>+ prompt_framework.compose()"]
    L --> M["agents/claude_client.py<br/>asyncio.create_subprocess_exec(<br/>'claude', '-p', prompt)<br/>120s timeout"]
    M --> N["agents/orchestrator.py<br/>assemble_turn()<br/>(merges narration + sidecar JSONL<br/>tool patches per ADR-059)"]

    N --> O["extract_location_header()"]
    O --> P["Update NPC registry"]
    P --> Q["Apply combat / encounter patches"]
    Q --> R["Merge quest updates"]
    R --> S["XP + level progression<br/>(partial — ADR-081 deferred)"]
    S --> T["Extract items → inventory"]

    T --> U["protocol/messages.py<br/>NARRATION{<br/>text, state_delta, footnotes}"]
    U --> V["protocol/messages.py<br/>NARRATION_END{state_delta}"]
    V --> W["+ PARTY_STATUS<br/>+ INVENTORY<br/>+ MAP_UPDATE<br/>+ COMBAT_EVENT<br/>+ CHAPTER_MARKER"]

    W --> X["server/websocket.py<br/>writer task → ws.send_json()"]
    X --> Z["Client: NARRATION<br/>(WebSocket JSON)"]

    style A fill:#4a9eff,color:#fff
    style Z fill:#4a9eff,color:#fff
    style Z2 fill:#4a9eff,color:#fff
    style M fill:#ff6b6b,color:#fff
```

**Key files:** `server/websocket.py` → `server/session_handler.py` → `agents/orchestrator.py` → `agents/claude_client.py` → back through `session_handler.py`

**Sidecar tool model (ADR-059):** the narrator emits prose only. Mechanical state changes (mood, intent, items, quests, SFX, resource deltas, personality events, scene renders) are written by sidecar tools to JSONL during narration. `assemble_turn` merges tool results with narration, with tool values always taking precedence over any prose extraction.

**Storage touched:** NPC registry, quest log, inventory, XP/level, narration history, lore store

---

## 2. Narrator Prompt Assembly

How the narrator prompt is composed across attention zones, with Full vs Delta tiering (ADR-066). Lives entirely in `sidequest-server/sidequest/agents/prompt_framework/`.

```mermaid
flowchart TD
    subgraph TRIGGER["Trigger"]
        A["server/session_handler.py<br/>dispatch_player_action()"]
    end

    A --> B["agents/orchestrator.py<br/>IntentRouter.classify_with_state()<br/>State override — no keyword matching"]
    B --> C{"Game state?"}
    C -->|"in_combat"| C1["Intent.Combat"]
    C -->|"in_chase"| C2["Intent.Chase"]
    C -->|"default"| C3["Intent.Exploration"]

    C1 & C2 & C3 --> D{"First turn<br/>of session?"}
    D -->|"yes"| E["Full Tier<br/>(~15KB system prompt)"]
    D -->|"no"| F["Delta Tier<br/>(dynamic state only)"]

    E & F --> G["agents/prompt_framework/<br/>core/ContextBuilder"]

    subgraph PRIMACY["Primacy Zone — Maximum Attention"]
        P1["narrator_identity"]
        P2["narrator_constraints<br/>Silent constraint handling"]
        P3["narrator_agency<br/>PC puppet prevention + multiplayer"]
        P4["narrator_consequences<br/>Genre tone alignment"]
        P5["narrator_output_only ★<br/>Sidecar-tool emission rules<br/>(prose only; tools handle patches)"]
        P6["genre_identity ★"]
    end

    subgraph EARLY["Early Zone — High Attention"]
        E1["narrator_output_style"]
        E2["narrator_combat_rules ★"]
        E3["narrator_chase_rules<br/>If in_chase"]
        E4["narrator_dialogue_rules ★"]
        E5["soul_principles<br/>From SOUL.md (filtered per agent)"]
        E6["trope_beat_directives<br/>(currently dark — ADR-087 RESTORE P1)"]
    end

    subgraph VALLEY["Valley Zone — Moderate Attention"]
        V1["game_state ★<br/>HP, inventory, quests,<br/>known facts, tropes,<br/>resources, party roster"]
        V2["ocean_personalities<br/>NPC behavioral summaries"]
        V3["ability_context<br/>Character involuntary abilities"]
        V4["world_lore<br/>Graph-filtered by distance<br/>(game/lore_*.py)"]
        V5["merchant_context<br/>(deferred — see ADR-087)"]
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
        R1["narrator_verbosity ★<br/>Length limits"]
        R2["opening_scene_constraint<br/>First-turn length cap"]
        R3["player_action ★"]
    end

    G --> PRIMACY --> EARLY --> VALLEY --> LATE --> RECENCY

    RECENCY --> H{"Tier?"}
    H -->|"Full"| I["claude --model opus<br/>--session-id {UUID}<br/>--system-prompt {zones}<br/>-p {action}"]
    H -->|"Delta"| J["claude --model opus<br/>--resume {session_id}<br/>-p {zones + action}"]

    I & J --> K["Parse response (prose only)<br/>+ collect sidecar tool JSONL"]
    K --> L["assemble_turn:<br/>merge narration with<br/>tool-emitted patches"]
    L --> M["ActionResult<br/>→ back to session_handler"]

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

**Delta tier key rule:** `narrator_output_only` (sidecar-tool emission rules) is re-sent every turn — without it, the narrator stops emitting structured tool calls.

**Token telemetry:** Per-zone token estimates emitted via OTEL spans for the Prompt Inspector dashboard (ADR-090, restoration in progress).

**Trope-beat directives are partial.** `TropeState` data is ported to Python; the engine that fires beats from progression (`apply_trope_engagement`) is on ADR-087's RESTORE P1 list. Until restored, trope-beat directives are emitted as best-effort by the narrator without engine guarantees.

---

## 3. Image Generation

Background pipeline — narration triggers render, result arrives asynchronously via RENDER_QUEUED → IMAGE replacement. Daemon side runs in `sidequest-daemon` (separate Python process, Unix socket per ADR-035).

```mermaid
flowchart TD
    A["ActionResult from narrator"] --> B{"visual_scene<br/>in tool emission?"}
    B -->|"yes"| C["Use narrator's visual_scene<br/>(tier, subject, mood, tags)"]
    B -->|"no"| D["Subject extractor<br/>(regex fallback)"]
    C & D --> E{"RenderSubject?"}
    E -->|"None"| Z1["No image this turn"]
    E -->|"Some(subject)"| F["Drama gate<br/>(inline in orchestrator)"]

    F --> G{"Valid?"}
    G -->|"rejected"| Z3["OTEL: relevance_rejected"]
    G -->|"valid"| H["Pacing throttle<br/>30s solo, 60s multi (ADR-050)"]

    H --> I{"Throttled?"}
    I -->|"yes"| Z2["Suppressed: cooldown / burst rate"]
    I -->|"no"| J["Render queue<br/>SHA256 content dedup"]

    J --> K["RENDER_QUEUED broadcast<br/>(render_id, tier, dimensions)"]
    K --> K2["Client: shimmer placeholder"]

    J --> L["Visual style lookup<br/>(visual_style.yaml)<br/>positive_suffix, negative_prompt,<br/>LoRA path, seed"]
    L --> M["daemon_client/<br/>Unix socket → /tmp/sidequest-renderer.sock<br/>RenderParams (300s timeout)"]

    M --> N["sidequest-daemon (Python)"]

    subgraph DAEMON["Daemon Pipeline"]
        N1["PromptComposer<br/>Tier prefix + subject + style<br/>T5 (512 tok) + CLIP (77 tok)<br/>+ negative prompt"]
        N2["FluxWorker / Z-ImageWorker<br/>Flux.1-dev (12 steps),<br/>Flux.1-schnell (4 steps),<br/>Z-Image Turbo"]
        N3["Optional: LoRA adapter<br/>(ADR-032 / 083 / 084)"]
        N4["Optional: IP-Adapter<br/>reference portrait (ADR-034)"]
        N1 --> N2
        N3 -.-> N2
        N4 -.-> N2
    end
    N --> N1

    N2 --> O["RenderResult<br/>{image_url, generation_ms}"]

    O --> Q{"image_url<br/>empty?"}
    Q -->|"yes"| Z4["Reject — no silent fallback (CLAUDE.md)"]
    Q -->|"no"| R["protocol/messages.py<br/>IMAGE{url, description, tier,<br/>scene_type, handout, render_id}"]

    R --> S["Client: replace shimmer<br/>with actual image<br/>(match by render_id)"]

    style A fill:#6c5ce7,color:#fff
    style S fill:#4a9eff,color:#fff
    style K2 fill:#4a9eff,color:#fff
    style N2 fill:#00b894,color:#fff
```

> ⚠️ **Port-drift status (ADR-087):**
> - Standalone `BeatFilter` module **dark** (RESTORE P3) — drama gate logic currently inline in orchestrator.
> - `SceneRelevanceValidator` **dark** (REDESIGN P2 under ADR-086 image-composition taxonomy).
> - `PrerenderScheduler` (speculative prerender, ADR-044) **dark** (RESTORE P2).

**Subject extraction:** Narrator's `visual_scene` (from sidecar tool emission) is preferred; regex fallback only.

**Render tiers:** portrait (768×1024), portrait_square (1024×1024), landscape (1024×768), scene_illustration (1024×768), text_overlay (768×512), fog_of_war (1024×1024). The `cartography` tier was removed 2026-04-28 along with the rest of the live world-map runtime view (ADR-019 superseded). The `tactical_sketch` tier was retired separately under ADR-086.

**Handout classification:** Discovery scenes and dialogue portraits flagged as `handout: true` → persisted in player journal.

---

## 4. TTS Voice Pipeline (removed)

The Kokoro TTS streaming pipeline was retired in **Epic 27 (MLX Image Renderer)**
when the sidequest-daemon was narrowed to a single-purpose Flux/Z-Image renderer.
The follow-up protocol cleanup landed in **ADR-076 / story 27-9**, which removed
the `NarrationChunk` message variant and `NarrationChunkPayload` from the
protocol module, and the corresponding UI narration buffer that was designed
to synchronize text reveal with incoming PCM voice frames.

Current narration delivery is the simplified two-message flow shown in
[Section 1 — Core Turn Loop](#1-core-turn-loop):

```
NARRATION { text, state_delta, footnotes }
NARRATION_END { state_delta }
```

The UI pairs `NARRATION` with its terminal `NARRATION_END` in a small buffer so
any end-of-turn `state_delta` applies in the same React commit as the narration
text. There is no longer any streaming-chunks leg, no binary voice frames, and
no audio ducking around speech. The audio mixer in `sidequest-daemon` runs
**two channels only** (music + SFX).

If TTS is reintroduced later, it will almost certainly use a different
streaming shape (e.g. a single `VoiceTrack` message with a URL reference, or
post-narration audio job queued like images are). See ADR-076 Alternatives
Considered for the rationale.

---

## 5. Music & Audio

Mood classification drives track selection over pre-rendered ACE-Step library tracks. Lives in `sidequest/audio/`.

```mermaid
flowchart TD
    A["Narration text"] --> B["audio/music_director.py<br/>MusicDirector.classify_mood()"]

    B --> C["MoodContext:<br/>in_combat, in_chase,<br/>party_health_pct,<br/>quest_completed, npc_died,<br/>scene_turn_count, drama_weight"]
    C --> D["MoodClassification:<br/>{primary: MoodKey, intensity, confidence}"]

    D --> E["audio/music_director.py<br/>MusicDirector.evaluate()"]
    E --> F["Look up mood_tracks<br/>from genre pack AudioConfig<br/>+ mood_aliases"]
    F --> G["Select variation<br/>(Overture / Resolution /<br/>TensionBuild / Ambient /<br/>Sparse / Full)"]

    G --> K["Top candidate<br/>(per-mood rotation history)"]

    K --> L["audio/audio_mixer.py<br/>apply_cue()"]
    L --> M["server/session_handler.py<br/>audio_cue_to_game_message()"]
    M --> N["protocol/messages.py<br/>AUDIO_CUE{<br/>mood, music_track,<br/>channel, action, volume}"]
    N --> O["Client: AUDIO_CUE → useAudioCue"]

    style A fill:#6c5ce7,color:#fff
    style O fill:#4a9eff,color:#fff
```

> ⚠️ **Port-drift status (ADR-087):** the standalone `ThemeRotator` module
> from the Rust era is **superseded** — TensionTracker plus narrative-weight
> traits (ADR-080) cover the pacing surface it provided. Per-mood rotation
> history is kept inline in `MusicDirector`. If a pacing gap surfaces later
> that the inline approach cannot serve, design fresh.

**Core moods (string-keyed, ADR-079):** Combat, Exploration, Tension, Triumph, Sorrow, Mystery, Calm. Genre packs declare any custom mood string in `audio.yaml` and map via `mood_aliases` to a core mood or directly to tracks.

**Variation selection (6-tier priority):** Overture (session start/location change) → Resolution (combat ended/quest completed) → TensionBuild (intensity ≥0.7 or drama ≥0.7) → Ambient (intensity ≤0.3 or scene turn ≥4) → Sparse (mid-intensity, low drama) → Full (fallback)

**MoodContext inputs:** in_combat, in_chase, party_health_pct, quest_completed, npc_died, encounter_mood_override, location_changed, scene_turn_count, drama_weight (from TensionTracker)

**2 channels:** music, sfx — each with independent volume and action (play/fade_in/fade_out/duck/restore/stop). Default volumes: music 0.7, sfx 0.8. The voice / TTS channel and ambience channel of earlier diagrams are **gone** (ADR-076).

**Client (useAudioCue.ts):** Routes AUDIO_CUE by action field — configure/duck/restore/fade_out/play. AudioEngine handles crossfade between tracks, AudioCache prevents re-decoding.

---

## 6. Multiplayer Turn Barrier

Sealed-letter pattern — all players submit, one elected handler resolves. Lives in `sidequest/server/session_room.py`.

```mermaid
flowchart TD
    A["Player A: PLAYER_ACTION"] --> B["session_handler.py<br/>turn_mode.should_use_barrier()?"]
    A2["Player B: PLAYER_ACTION"] --> B2["session_handler.py<br/>should_use_barrier()?"]

    B -->|"Structured/Cinematic"| C["session_room.py<br/>TurnBarrier.submit_action(<br/>player_a, action_a)"]
    B2 -->|"Structured/Cinematic"| C2["session_room.py<br/>TurnBarrier.submit_action(<br/>player_b, action_b)"]

    C --> D["session_room.py<br/>record_action() → dict"]
    C2 --> D

    D --> E["session_room.py<br/>is_barrier_met()?<br/>active_turn_takers reached<br/>(story 45-2: lobby vs active)"]
    E -->|"yes"| F["asyncio.Event.set()"]
    E -->|"no, wait"| G["session_room.py<br/>wait_for_turn()<br/>asyncio.wait({<br/>  event.wait(),<br/>  asyncio.sleep(adaptive_timeout)<br/>}, return_when=FIRST_COMPLETED)"]

    G -->|"timeout"| H["force_resolve_turn()<br/>'hesitates, waiting'"]
    F --> I["session_room.py<br/>resolution_lock acquire"]
    H --> I

    I --> J["try_claim_resolution()"]
    J -->|"true (first caller)"| K["Elected handler:<br/>combined actions<br/>→ narrator with PARTY ACTIONS block"]
    J -->|"false (others)"| L["Non-elected:<br/>receive narration<br/>via session broadcast"]

    K --> M["agents/orchestrator.py<br/>narrator result"]
    M --> M2["game/shared_world_delta.py<br/>emit minimal delta seed for<br/>next player's turn (story 45-1)"]
    M2 --> N["session_handler.py<br/>broadcast to co-located players"]
    N --> O["agents/perception_rewriter.py<br/>per-player narration variant"]
    O --> P["All players: NARRATION"]

    M --> Q["protocol/messages.py<br/>TURN_STATUS 'resolved'<br/>(global broadcast)"]

    style A fill:#4a9eff,color:#fff
    style A2 fill:#4a9eff,color:#fff
    style P fill:#4a9eff,color:#fff
```

**Adaptive timeout:** 3s for 2-3 players, 5s for 4+ (configurable tiers)

**Resolution lock:** `asyncio.Lock` ensures exactly one task calls the narrator — others receive broadcast.

**Active turn-takers (story 45-2):** Barrier counts players whose characters have advanced past round 0, not raw lobby connections. Phantom lobby peers no longer block solo turns. OTEL emits `lobby_participant_count` vs `active_turn_count` on every barrier wait.

**Shared-world delta (story 45-1):** After each turn, `shared_world_delta` emits a minimal delta (current location, active encounter id, party formation/adjacency) that seeds the next player's turn so the narrator stops fabricating physical separations between party members.

**Perception filter:** If a player has perceptual effects active, their narration copy is prefixed with `[Your perception is altered: ...]`.

**Sealed-letter dispatch handler:** dark — see ADR-087 RESTORE P1. The barrier mechanism above lives in session_room; the **dedicated dispatch handler** that some scenarios route through is on the restoration roster.

---

## 7. Combat & Encounter Flow

State-override detection (ADR-067, no keyword matching), structured mutations, and CombatOverlay broadcast.

```mermaid
flowchart TD
    A["Player action"] --> B["agents/orchestrator.py<br/>IntentRouter.classify_with_state()<br/>ADR-067: state override only"]
    B --> C{"in_combat == true?"}
    C -->|"yes"| D["Intent.Combat<br/>source: StateOverride<br/>confidence: 1.0"]
    C -->|"no"| E["Intent.Exploration<br/>(or Chase if in_chase)"]

    D --> F["Narrator agent responds;<br/>sidecar tools emit<br/>combat patches"]
    E --> F

    F --> G["game/encounter.py<br/>apply_state_mutations()"]

    G --> H{"combat_patch<br/>.in_combat?"}
    H -->|"Some(true) &<br/>!was_in_combat"| I["EncounterState.engage()<br/>Build turn order<br/>Register combatants<br/>TurnMode: FreePlay → Structured<br/>Activate turn barrier"]
    H -->|"Some(false) &<br/>was_in_combat"| J["EncounterState.disengage()<br/>Clear turn order, reset rounds<br/>TurnMode: Structured → FreePlay"]
    H -->|"None / no change"| K["Continue in current state"]

    G --> L["Apply HP changes"]
    L --> L1{"Target == player?"}
    L1 -->|"yes"| L2["clamp_hp(hp, delta, max_hp)<br/>OTEL: hp_change"]
    L1 -->|"no"| L3["npc_registry[target].hp += delta"]

    I & J & K --> M["server/dispatch/<br/>process_combat_and_chase()"]
    L2 & L3 --> M

    M --> N["Tick status effects<br/>(decay durations)"]
    N --> O["Build enemies list<br/>from turn_order + NPC registry"]
    O --> P["CombatEnemy per NPC:<br/>{name, hp, max_hp, ac,<br/>status_effects[]}"]

    P --> Q["protocol/messages.py<br/>COMBAT_EVENT{<br/>in_combat, enemies,<br/>turn_order, current_turn}"]
    Q --> R["WebSocket broadcast"]

    R --> S["App.tsx: setCombatState()"]
    S --> T["CombatOverlay renders:<br/>Turn order (current highlighted)<br/>Enemy HP bars (color-coded)<br/>Status effects + remaining rounds"]

    style A fill:#4a9eff,color:#fff
    style T fill:#4a9eff,color:#fff
    style F fill:#ff6b6b,color:#fff
```

> ⚠️ **Port-drift status (ADR-087):** the chase engine (`chase_depth.rs`,
> `chase.rs`) **did not port**. There is no `chase.py` or `chase_depth.py` in
> the Python tree; only string references in `game/encounter.py`. ADR-087
> verdict: **RESTORE P2** under ADR-017. Chase intent still classifies
> correctly (state-override) but engine-side terrain, rig physics, and
> phase mechanics are not enforced.

**No keyword matching** — combat detection is purely state-driven (ADR-067). `in_combat` flag in game state triggers Intent.Combat.

**Turn mode FSM:** `FreePlay` ↔ `Structured` (on combat start/end), `FreePlay` → `Cinematic` (on cutscene)

**Encounter tracking:** round counter, turn_order, current_turn, damage log, status effects (Poison/Stun/Bless/Curse with duration decay), drama_weight, available_actions.

**HP bar colors:** green (>50%), orange (25-50%), red (<25%). Status indicators: "bloodied" at 50%, "defeated" at 0 HP.

**Confrontation engine (Epic 16/28):** `game/resource_pool.py` and the typed-confrontation framework ported. **VERIFY → likely RESTORE P0** per ADR-087 — Epic 28 was the largest body of work immediately pre-port and per-story landing has not been verified.

---

## 8. Character Creation

Genre-driven scene-based state machine with bidirectional messages.

```mermaid
flowchart TD
    A["SESSION_EVENT{connect}<br/>genre, world, player_name"] --> B["session_handler.py<br/>persistence.exists()?"]
    B -->|"returning"| C["Load GameSnapshot<br/>→ skip creation<br/>→ Playing state"]
    B -->|"new"| D["SESSION_EVENT{connected,<br/>has_character: false}"]

    D --> E["game/builder.py<br/>CharacterBuilder.try_new()<br/>(genre scenes + rules)"]
    E --> F["builder.to_scene_message()<br/>→ CHARACTER_CREATION<br/>{phase: 'scene', scene_index,<br/>choices, allows_freeform}"]

    F --> G["Client: show scene"]
    G --> H["Client: CHARACTER_CREATION<br/>{phase: 'scene', choice}"]
    H --> I["session_handler.py<br/>builder.apply_choice(index)"]
    I --> J{"More scenes?"}
    J -->|"yes"| F
    J -->|"no"| K["CHARACTER_CREATION<br/>{phase: 'confirmation',<br/>character_preview}"]

    K --> L["Client: confirm"]
    L --> M["session_handler.py<br/>builder.build(player_name)"]
    M --> N["AccumulatedChoices →<br/>Character with CreatureCore<br/>(HP, AC, abilities, inventory)"]
    N --> O["CHARACTER_CREATION<br/>{phase: 'complete', character}"]
    O --> P["Session → Playing state"]
    P --> Q["game/lore_seeding.py<br/>LoreStore seeded from<br/>creation choices"]
    Q --> R["game/region_init.py<br/>seed snap.current_region<br/>from world cartography.yaml"]

    style A fill:#4a9eff,color:#fff
    style G fill:#4a9eff,color:#fff
    style L fill:#4a9eff,color:#fff
```

**Accumulated from scenes:** class, race, personality, items, affinity, backstory fragments, stat bonuses, pronouns, rig type, catch phrase

**3 creation modes (ADR-016):** Menu (pick from list), Guided (follow prompts), Freeform (describe anything)

**Region init:** Region/route world topology (`CartographyConfig`) lives in `world.cartography.yaml` and seeds `snap.current_region` at chargen — this is the residual cartography wiring that survived the 2026-04-28 ADR-019 supersession. The live runtime world-map view is gone.

---

## 9. Pacing & Drama Engine

Dual-track tension model drives narration length and delivery speed. Lives in `sidequest/game/tension_tracker.py`.

```mermaid
flowchart TD
    A["Each turn: combat events,<br/>HP changes, action results"] --> B["game/tension_tracker.py<br/>TensionTracker.observe()"]
    B --> C["Classify: Boring/Dramatic/Normal"]
    C --> D["Update action_tension<br/>(gambler's ramp)"]
    D --> E["Inject event spikes<br/>(critical hit, death save)"]

    F["Each turn"] --> G["game/tension_tracker.py<br/>TensionTracker.tick()"]
    G --> H["action_tension *= 0.9<br/>(ACTION_DECAY)"]
    H --> I["Age existing spikes<br/>(linear decay)"]

    I --> J["drama_weight =<br/>max(action, stakes, spike)"]
    J --> K["pacing_hint()"]

    K --> L{"drama_weight<br/>thresholds"}
    L -->|"> streaming_min"| M["DeliveryMode.Streaming<br/>(word-by-word)"]
    L -->|">= sentence_min"| N["DeliveryMode.Sentence<br/>(sentence-by-sentence)"]
    L -->|"< sentence_min"| O["DeliveryMode.Instant<br/>(full text)"]

    K --> P["PacingHint.<br/>narrator_directive()"]
    P --> Q["'Target N sentences.<br/>Drama level: X%.'"]

    K --> R{"boring_streak >=<br/>escalation_streak?"}
    R -->|"yes"| S["Inject escalation beat"]
    R -->|"no"| T["No escalation"]

    Q --> U["agents/prompt_framework/<br/>register_pacing_section()<br/>Late attention zone"]
    S --> U
    U --> V["Narrator prompt<br/>(length + urgency guidance)"]

    style V fill:#ff6b6b,color:#fff
```

**Genre-tunable:** `pacing.yaml` in genre pack sets `streaming_delivery_min`, `sentence_delivery_min`, `escalation_streak`

**Dual tracks:** Action tension (gambler's ramp from boring streaks) + Stakes tension (HP ratio) + Event spikes (discrete dramatic moments)

---

## 10. Knowledge Pipeline

Narrator footnotes become persistent facts that feed back into future prompts. Lives in `sidequest/game/lore_*.py` + `sidequest/game/character.py` (KnownFact).

```mermaid
flowchart TD
    A["Narrator response:<br/>prose + sidecar tool emissions"] --> B["agents/orchestrator.py<br/>assemble_turn extracts<br/>footnotes from tool JSONL"]
    B --> C["footnotes: list[Footnote]<br/>{marker, summary, category,<br/>is_new, fact_id}"]

    C --> D["session_handler.py<br/>Attach to NarrationPayload<br/>(sent to client)"]
    D --> E["Client: render [N] superscripts<br/>+ footnote entries below narration"]

    C --> F["game/footnote_to_fact.py<br/>footnotes_to_discovered_facts()"]
    F --> G{"is_new?"}
    G -->|"true"| H["Create DiscoveredFact<br/>{content, category, turn,<br/>source: Discovery,<br/>confidence: Certain}"]
    G -->|"false"| I["Callback to existing<br/>KnownFact via fact_id"]

    H --> J["Character.known_facts<br/>accumulation"]
    J --> K["Next turn:<br/>agents/prompt_framework/<br/>register_knowledge_section()"]
    K --> L["[CHARACTER's KNOWLEDGE]<br/>Top 20 facts by recency<br/>with confidence tags<br/>Valley attention zone"]
    L --> M["Narrator prompt<br/>(don't-repeat constraint)"]

    H --> N["game/lore_store.py<br/>accumulate_lore()"]
    N --> O["game/lore_seeding.py<br/>+ game/lore_embedding.py<br/>select_lore_for_prompt()<br/>(budget-aware, keyword-hinted,<br/>cross-process embedding via<br/>daemon per ADR-048)"]
    O --> P["Narrator/agent prompts<br/>(grounding zone)"]

    style A fill:#6c5ce7,color:#fff
    style E fill:#4a9eff,color:#fff
    style M fill:#ff6b6b,color:#fff
    style P fill:#ff6b6b,color:#fff
```

**FactCategory:** Lore, Place, Person, Quest, Ability

**Lore budget:** Token-aware selection prevents prompt bloat (content.len / 4 token estimate).

**Lore filter:** dark — see ADR-087 RESTORE P2. Suitability filtering of LLM-output lore mint is currently absent.

**Feedback loop:** Footnotes → KnownFacts → prompt injection → narrator avoids repeating → new footnotes

---

## 11. NPC Personality (OCEAN)

Big Five profiles loaded from genre packs, summarized into narrator prompts. Lives in `sidequest/genre/models/ocean.py`.

```mermaid
flowchart TD
    A["Genre pack YAML<br/>archetypes.yaml"] --> B["genre/loader.py<br/>+ resolver.py"]
    B --> C["NPC pydantic model<br/>ocean: OceanProfile | None"]

    C --> D["genre/models/ocean.py<br/>OceanProfile.behavioral_summary()"]
    D --> E{"Score thresholds"}
    E -->|"<= 3.0"| F["Low descriptor<br/>(e.g., 'reserved', 'blunt')"]
    E -->|">= 7.0"| G["High descriptor<br/>(e.g., 'gregarious', 'meticulous')"]
    E -->|"3.1 - 6.9"| H["Omitted (neutral)"]

    F & G --> I["Joined string:<br/>'reserved and meticulous,<br/>curious and imaginative'"]
    H --> J["Fallback:<br/>'balanced temperament'"]

    I --> K["agents/prompt_framework/<br/>register_ocean_personalities_section()"]
    J --> K
    K --> L["## NPC Personalities<br/>- Grimjaw: cautious and stubborn<br/>- Lyra: gregarious and creative<br/>Valley attention zone"]
    L --> M["Narrator prompt"]

    C --> N["[ocean_shift_proposals]<br/>port-drift: ABSENT in Python<br/>ADR-087 RESTORE P2"]
    N -.->|"future"| O["Post-narration pipeline:<br/>detect PersonalityEvents →<br/>apply shifts → log"]

    style A fill:#fdcb6e,color:#333
    style M fill:#ff6b6b,color:#fff
    style N fill:#b2bec3,color:#333
```

**5 dimensions:** Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism (0.0-10.0)

**Agreeableness → Disposition:** A-dimension feeds the `npc.disposition` scalar. The full Attitude enum + transition system from the Rust era **did not port** — disposition is currently a plain int with clamping. ADR-087 verdict: **RESTORE P1** under ADR-020.

**Gap:** OCEAN shift proposals — the engine that detects personality events from narration and applies live shifts — **did not port**. Model is present, pipeline is missing. ADR-042 design stands; restoration is on ADR-087's P2 list.

---

## 12. Faction Agendas & Scene Directives

Factions pursue goals that inject into every narrator turn. Data is ported; agenda urgency feeds scene directive injection.

```mermaid
flowchart TD
    A["Genre pack world YAML<br/>factions section"] --> B["genre/loader.py<br/>FactionAgenda parse"]
    B --> C["FactionAgenda<br/>{faction_name, goal,<br/>urgency, event_text}"]

    C --> D{"urgency"}
    D -->|"Dormant"| E["Filtered out"]
    D -->|"Simmering/Pressing/Critical"| F["game/scene_directive.py<br/>agenda.scene_injection()"]

    F --> G["scene_directive.format()"]

    H["Trope state:<br/>fired_beats<br/>(currently best-effort —<br/>engine on ADR-087 RESTORE P1)"] --> G
    I["Active stakes"] --> G

    G --> J["SceneDirective<br/>{trope_beats, faction_events,<br/>active_stakes, hints}"]
    J --> K["agents/prompt_framework/<br/>register_scene_directive()"]
    K --> L["render_scene_directive()"]
    L --> M["[SCENE DIRECTIVES — MANDATORY]<br/>Priority-sorted elements:<br/>- TropeBeat instructions<br/>- FactionEvent injections<br/>- ActiveStake markers<br/>Early attention zone"]
    M --> N["Narrator prompt<br/>(high priority, after identity)"]

    style A fill:#fdcb6e,color:#333
    style N fill:#ff6b6b,color:#fff
```

**Urgency levels:** Dormant (filtered), Simmering, Pressing, Critical

**Mandatory weave:** Scene directives use EARLY attention zone — narrator must incorporate them

---

## 13. Slash Commands

Server-side interception before intent classification. Python-era home is `sidequest/game/commands.py` (was server dispatch in Rust).

```mermaid
flowchart TD
    A["PLAYER_ACTION<br/>{action: '/status'}"] --> B["session_handler.py<br/>slash router check"]
    B --> C["game/commands.py<br/>try_dispatch(input, state)"]
    C --> D{"starts with '/'?"}
    D -->|"no"| E["Pass through to<br/>intent classification"]
    D -->|"yes"| F["Parse: command + args"]

    F --> G{"command"}
    G --> H["/status → StatusCommand"]
    G --> I["/inventory → InventoryCommand"]
    G --> J["/map → MapCommand"]
    G --> K["/save → SaveCommand"]
    G --> L["/help → Built-in list"]
    G --> M["/tone → ToneChange (ADR-052)"]
    G --> N["/gm → GM suite<br/>(set, teleport, spawn, dmg)"]

    H --> O["CommandResult.Display(text)"]
    I --> P["CommandResult.Display(text)"]
    N --> Q["CommandResult.StateMutation(patch)"]
    M --> R["CommandResult.ToneChange(axes)"]

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

**No LLM call:** Slash commands resolve mechanically — no Claude subprocess, no intent classification.

**GM commands:** Protected by role check, allow direct state manipulation for debugging.

---

## 14. Trope Engine ⚠️ partial

> ⚠️ **Port-drift status (ADR-087 RESTORE P1, ADR-018 still accepted):**
> `TropeState` data ported to `sidequest/game/session.py` and progresses each
> turn, but the Rust `apply_trope_engagement` engine (driver selection,
> engagement outcomes, beat firing from threshold crossings) **did not
> port**. The diagram below describes the **design intent** of ADR-018; the
> "Fire beat" branch is currently best-effort by the narrator without engine
> guarantees. Restoration is wiring the engine back onto existing data.

```mermaid
flowchart TD
    A["Genre pack tropes.yaml<br/>+ world overrides"] --> B["TropeDefinition<br/>{id, name, beats at thresholds,<br/>stakes, NPCs, themes}"]
    B --> C["Session init:<br/>TropeState per definition<br/>(progression: 0.0)"]

    D["Each turn"] --> E["Passive tick:<br/>progression += genre_rate"]
    E --> F{"progression crosses<br/>beat threshold?"}
    F -->|"yes"| G["Fire beat (intent):<br/>FiredBeat{name, event,<br/>stakes, npcs, hints}<br/>⚠️ engine missing"]
    F -->|"no"| H["No beat this turn"]

    G --> I["agents/subsystems/troper/<br/>build_beats_context()<br/>(scaffolding present;<br/>engagement outcomes dark)"]
    I --> J["[TROPE BEATS — MANDATORY WEAVE]<br/>Per beat:<br/>  TROPE: name + threshold%<br/>  BEAT EVENT: instruction<br/>  STAKES: what's at risk<br/>  NPCS INVOLVED: list<br/>  NARRATIVE HINTS: enriched<br/>Early attention zone"]

    K["Active tropes (progressing)"] --> L["active trope summary"]
    L --> M["Background context on<br/>progressing narrative arcs"]

    J --> N["Narrator prompt"]
    M --> N

    G --> O["scene_directive.py<br/>Also injected into<br/>SceneDirective.trope_beats"]

    style A fill:#fdcb6e,color:#333
    style N fill:#ff6b6b,color:#fff
    style G fill:#b2bec3,color:#333
```

**Trope lifecycle (intent):** Progression 0.0 → 1.0 with beats firing at defined thresholds.

**Engagement multiplier (intent):** Scale progression rate by player engagement (turns_since_meaningful). Engine on ADR-087 P1.

---

## 15. Session Persistence

Atomic save after every turn, full recovery on reconnect. Lives in `sidequest/game/persistence.py` (stdlib `sqlite3` via `asyncio.to_thread`).

```mermaid
flowchart TD
    A["Turn completes"] --> B["session_handler.py<br/>Build GameSnapshot<br/>(all session state)"]
    B --> C["session_handler.py<br/>persistence.save()"]
    C --> D["asyncio.to_thread(<br/>SqliteStore.save)"]

    D --> E["game/persistence.py<br/>SqliteStore.save()"]
    E --> F["json.dumps<br/>(full GameSnapshot)"]
    F --> G["sqlite3 transaction:<br/>INSERT OR REPLACE<br/>game_state(snapshot_json)"]

    H["Narration text"] --> I["game/persistence.py<br/>append_narrative()"]
    I --> J["INSERT narrative_log<br/>(round, author, content, tags)"]

    K["Client reconnects<br/>SESSION_EVENT{connect}"] --> L["session_handler.py<br/>persistence.exists()?"]
    L -->|"true"| M["SqliteStore.load()"]
    M --> N["SELECT snapshot_json<br/>FROM game_state"]
    N --> O["json.loads + pydantic validate<br/>→ GameSnapshot"]
    O --> P["Restore all session state:<br/>character, location, quests,<br/>NPCs, tropes, inventory,<br/>axis values, lore"]
    P --> Q["Generate recap from<br/>recent narrative_log entries"]
    Q --> R["SESSION_EVENT{ready}<br/>with initial_state + recap"]

    style A fill:#6c5ce7,color:#fff
    style K fill:#4a9eff,color:#fff
    style R fill:#4a9eff,color:#fff
    style G fill:#e17055,color:#fff
    style J fill:#e17055,color:#fff
```

**Schema:** 3 tables — `session_meta`, `game_state` (single row, full JSON), `narrative_log` (append-only)

**Async pattern:** `sqlite3.Connection` is not safely shareable across asyncio tasks — DB calls run on a worker thread via `asyncio.to_thread` at the async boundary.

**One DB per session:** `~/.sidequest/saves/{genre}/{world}/{player}/save.db`

**GameSnapshot includes:** characters, NPCs, encounter, chase data (where ported), tropes (full TropeState), quests, lore, axis values, achievements, campaign maturity, world history, NPC registry

---

## 16. Genre Pack Loading

Lazy binding — packs loaded per-session on connect, not at startup. Lives in `sidequest/genre/loader.py`.

```mermaid
flowchart TD
    A["Server starts<br/>SIDEQUEST_GENRE_PACKS env<br/>or CLI flag"] --> B["AppState stores path<br/>(no eager loading)"]

    C["Player connects<br/>SESSION_EVENT{connect}<br/>{genre: 'caverns_and_claudes',<br/>world: 'grimvault'}"] --> D["session_handler.py<br/>GenreLoader.load(genre_slug)"]

    D --> E["genre/loader.py<br/>load_genre_pack(path)"]
    E --> F["Read YAML files (PyYAML):"]
    F --> G["pack.yaml → PackMeta"]
    F --> H["rules.yaml → RulesConfig"]
    F --> I["lore.yaml → Lore"]
    F --> J["archetypes.yaml → NpcArchetypes"]
    F --> K["char_creation.yaml → Scenes"]
    F --> L["visual_style.yaml → VisualStyle"]
    F --> M["audio.yaml → AudioConfig"]
    F --> N["axes.yaml → AxesConfig"]
    F --> O["tropes.yaml → TropeDefinitions"]
    F --> P["cultures.yaml, pacing.yaml,<br/>voice_presets.yaml,<br/>lethality_policy.yaml,<br/>power_tiers.yaml,<br/>visibility_baseline.yaml,<br/>projection.yaml, etc."]
    F --> Q["worlds/ → World per slug<br/>(world.yaml, lore.yaml,<br/>cartography.yaml, history,<br/>archetypes, tropes, legends)"]

    E --> R["GenrePack (pydantic v2)"]

    R --> S["Initialize session state:"]
    S --> T["axes_config ← pack.axes"]
    S --> U["trope_defs ← pack.tropes + world overrides"]
    S --> V["visual_style ← pack + world overrides"]
    S --> W["music_director ← pack.audio"]
    S --> X["lore_store ← seeded from pack.lore"]
    S --> Y["voice_router ← pack.voice_presets<br/>(rendering only — no TTS)"]
    S --> Z["region/route ← world.cartography (chargen seed)"]

    style C fill:#4a9eff,color:#fff
    style R fill:#fdcb6e,color:#333
```

**15+ YAML files** per genre pack, all deserialized into typed pydantic models via PyYAML.

**World inheritance:** World-level overrides merge with genre-level defaults (tropes, visual style).

**Lazy binding (ADR-004):** Server starts genre-agnostic; genre bound at runtime on player connect.

**Production vs workshop:** `SIDEQUEST_GENRE_PACKS` always points at `sidequest-content/genre_packs/`. Five packs are functionally loadable (`caverns_and_claudes`, `elemental_harmony`, `mutant_wasteland`, `space_opera`, `victoria`); two production directories (`heavy_metal`, `spaghetti_western`) are empty shells with their content still in `sidequest-content/genre_workshopping/`. Four other packs (`low_fantasy`, `neon_dystopia`, `pulp_noir`, `road_warrior`) are workshop-only. See `docs/genre-pack-status.md`.

---

## Color Legend

```
Blue   (#4a9eff)  — Client/WebSocket messages (visible to player)
Purple (#6c5ce7)  — Internal data (narration text, results)
Red    (#ff6b6b)  — Claude CLI subprocess / narrator prompt
Green  (#00b894)  — Python daemon (Flux / Z-Image gen)
Orange (#e17055)  — SQLite persistence
Yellow (#fdcb6e)  — YAML configuration (genre packs)
Gray   (#b2bec3)  — Not yet wired in Python (port-drift; see ADR-087)
```

## Port-Drift Reference

Subsystems flagged with ⚠️ port-drift in this document have a verdict and tier
in `docs/adr/087-post-port-subsystem-restoration-plan.md`. The full
side-by-side inventory is at `docs/port-drift-feature-audit-2026-04-24.md`
(plus 2026-04-30 follow-up §9). Per ADR-082, the language port is complete;
per ADR-087, subsystem restoration is sequential P0 → P3 work.
