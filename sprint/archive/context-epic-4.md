# Epic 4: Media Integration — Wire sidequest-daemon for Images, TTS, and Audio

## Overview

Connect the Rust game server to the Python media daemon (sidequest-daemon) so that
gameplay produces rendered images, synthesized voice narration, and adaptive music.
The daemon stays Python — it owns the GPU-heavy generation pipelines (Flux/SDXL for
images, Kokoro/Piper for TTS, MusicGen for audio). The Rust server's job is to decide
*what* to generate, *when* to generate it, and *how* to deliver results to the React
client via WebSocket.

Three subsystems cross this boundary: image rendering, text-to-speech, and audio/music.
Each has its own pipeline with distinct latency profiles and caching strategies. The
beat filter and speculative prerendering are the two novel components — everything else
is plumbing.

## Background

### What the Daemon Already Does

sidequest-daemon is a working Python service with these endpoints:

| Subsystem | Daemon Component | What It Does |
|-----------|-----------------|--------------|
| **Images** | `renderer/` | Flux/SDXL generation, prompt composition, LoRA selection |
| **TTS** | `tts/` | Kokoro + Piper voice synthesis, streaming audio chunks |
| **Audio** | `audio/` | Library playback, MusicGen generation, mood-based track selection |
| **Scene** | `scene/` | Scene interpreter, subject extraction from narration text |

### Python Reference Code

| Rust Concept | Python Source | What to Port |
|--------------|--------------|-------------|
| Daemon HTTP client | `sq-2/sidequest/media/` | Request/response contract, retry logic |
| Subject extraction | `sq-2/sidequest/renderer/subject.py` | Entity/scene classification from narration |
| Beat filter | `sq-2/sidequest/renderer/filter.py` | Narrative significance scoring |
| Voice routing | `sq-2/sidequest/voice/router.py` | Character-to-voice-preset mapping |
| Text segmentation | `sq-2/sidequest/voice/segment.py` | Breaking narration into speakable chunks |
| Music director | `sq-2/sidequest/audio/director.py` | Mood extraction, track selection |
| Audio mixer | `sq-2/sidequest/audio/mixer.py` | 3-channel mixing, ducking coordination |

### What the React UI Already Has

The frontend already handles media playback — it just needs the right messages:
- `IMAGE` message displays a rendered scene image
- `AUDIO_CUE` message triggers music/SFX/ambience changes
- TTS audio streams play through the existing voice pipeline
- The UI manages its own audio context and volume controls

### Genre Pack Media Config

Genre packs define all media parameters in YAML:

```yaml
media:
  art_style: "dark fantasy oil painting"
  image_model: "flux-schnell"
  voice_presets:
    narrator: { model: "kokoro", voice: "en_male_deep", speed: 0.95 }
    default_npc: { model: "piper", voice: "en_US-lessac-medium" }
  mood_tracks:
    combat: ["battle_drums_01", "steel_clash_02"]
    exploration: ["forest_ambient_01", "tavern_hearth_01"]
    tension: ["suspense_strings_01"]
  sfx_library:
    sword_hit: "metal_clash_01.wav"
    spell_cast: "arcane_whoosh_01.wav"
```

## Technical Architecture

### System Boundary

```
┌─────────────────────────────────┐     HTTP POST      ┌──────────────────────────┐
│         Rust Server             │ ──────────────────► │    sidequest-daemon      │
│  (sidequest-api)                │                     │    (Python)              │
│                                 │ ◄────────────────── │                          │
│  ┌───────────┐  ┌────────────┐  │   JSON response     │  ┌─────────┐            │
│  │ Beat      │  │ Subject    │  │   (or chunked       │  │ Flux/   │            │
│  │ Filter    │  │ Extractor  │  │    stream for TTS)   │  │ SDXL    │            │
│  ├───────────┤  ├────────────┤  │                     │  ├─────────┤            │
│  │ Render    │  │ Voice      │  │                     │  │ Kokoro/ │            │
│  │ Queue     │  │ Router     │  │                     │  │ Piper   │            │
│  ├───────────┤  ├────────────┤  │                     │  ├─────────┤            │
│  │ Music     │  │ Audio      │  │                     │  │ MusicGen│            │
│  │ Director  │  │ Mixer Ctrl │  │                     │  │ Library │            │
│  └───────────┘  └────────────┘  │                     │  └─────────┘            │
│         │                       │                     └──────────────────────────┘
│         ▼                       │
│  WebSocket broadcast            │
│  IMAGE / AUDIO_CUE / TTS msgs  │
│         │                       │
└─────────┼───────────────────────┘
          ▼
   ┌──────────────┐
   │  React UI    │
   │  (playback)  │
   └──────────────┘
```

### Image Pipeline

```
narration text
      │
      ▼
Subject Extractor (4-2)
  parse entities, scene type, tier classification
      │
      ▼
Beat Filter (4-3)
  narrative_weight < threshold? ──► suppress (no render)
      │ (passes)
      ▼
Render Queue (4-4)
  hash-based dedup, async tokio::spawn
      │
      ▼
HTTP POST /render ──► daemon generates ──► response with image URL/bytes
      │
      ▼
IMAGE broadcast (4-5) ──► WebSocket ──► React displays
```

### TTS Pipeline

```
narration text
      │
      ▼
Voice Router (4-6)
  character ID ──► genre pack voice preset lookup
      │
      ▼
Text Segmenter (4-7)
  break into speakable segments (sentence boundaries, pause markers)
      │
      ▼
TTS Streaming (4-8)
  HTTP POST /tts per segment ──► daemon synthesizes
      │                              │
      ▼                              ▼
  Stream audio chunks to client via WebSocket
```

### Audio Pipeline

```
narration text
      │
      ▼
Music Director (4-9)
  mood extraction (combat/exploration/tension/triumph)
      │
      ├──► Theme Rotation (4-11) — anti-repetition within mood category
      │
      ▼
Audio Mixer Coordination (4-10)
  3-channel commands: music, SFX, ambience
  duck music during TTS playback
      │
      ▼
AUDIO_CUE broadcast ──► WebSocket ──► React audio context
```

### Key Types

```rust
/// HTTP client for all daemon communication
pub struct DaemonClient {
    http: reqwest::Client,
    base_url: Url,
    timeout: Duration,
}

/// Subject extracted from narration for image rendering
pub struct RenderSubject {
    pub entities: Vec<String>,
    pub scene_type: SceneType,
    pub tier: SubjectTier,  // Portrait, Scene, Landscape, Abstract
    pub prompt_fragment: String,
}

/// Queued render job with dedup
pub struct RenderJob {
    pub subject: RenderSubject,
    pub content_hash: u64,
    pub genre_art_style: String,
    pub status: RenderStatus,
}

/// Voice routing result
pub struct VoiceAssignment {
    pub character_id: String,
    pub model: TtsModel,       // Kokoro | Piper
    pub voice_id: String,
    pub speed: f32,
}

/// Audio mixing command sent to client
pub struct AudioCue {
    pub channel: AudioChannel,  // Music | Sfx | Ambience
    pub action: AudioAction,    // Play | FadeIn | FadeOut | Duck | Stop
    pub track_id: String,
    pub volume: f32,
}
```

## Story Dependency Graph

```
2-5 (orchestrator turn loop)
 │
 └──► 4-1 (daemon HTTP client)
       │
       ├──► 4-2 (subject extraction)
       │     │
       │     ├──► 4-3 (beat filter)
       │     │
       │     └──► 4-4 (render queue + cache dedup)
       │           │
       │           └──► 4-5 (IMAGE broadcast)
       │                 │
       ├──► 4-6 (voice routing)           │
       │     │                            │
       │     └──► 4-7 (text segmentation) │
       │           │                      │
       │           └──► 4-8 (TTS streaming)
       │                 │
       │                 └──────────┐
       │                            ▼
       │                      4-12 (speculative prerendering)
       │                        (also depends on 4-4)
       │
       └──► 4-9 (music director — mood extraction)
             │
             ├──► 4-10 (audio mixer coordination)
             │
             └──► 4-11 (theme rotation — anti-repetition)
```

## Deferred (Not in This Epic)

- **Daemon health monitoring** — Checking if the daemon is up before queuing work.
  Handled by timeout/retry in 4-1; dedicated health checks deferred.
- **Image caching persistence** — The render queue deduplicates in-memory via content
  hash. Persisting the cache to disk for cross-session reuse is deferred.
- **Voice cloning** — Custom voice training from audio samples. The voice router maps
  to existing presets; cloning is a daemon-side feature for later.
- **Client-side audio mixing** — The React UI already manages its own audio context.
  The Rust server sends cue commands; the client decides actual volume curves.
- **SFX triggering from game events** — Combat hit sounds, spell effects, etc. Genre
  packs define an SFX library, but wiring individual game events to specific SFX is
  deferred to a follow-up epic.

## Dependencies

### From Epic 2 (must complete first)
- Story 2-5: Orchestrator turn loop (4-1 depends on this — the daemon client is called
  from the turn pipeline after narration is generated)

### Cross-Story Dependencies Within Epic 4
- 4-12 (speculative prerendering) depends on both 4-4 (render queue) and 4-8 (TTS
  streaming) — it queues renders during the voice playback window

### External
- sidequest-daemon must be running with its render/TTS/audio endpoints available
- Genre pack YAML must include `media` section with art style, voice presets, and mood
  tracks

## Success Criteria

During a playtest session:
1. Narration-significant moments produce rendered images displayed in the React UI
2. Mundane actions (walking, looking around) are suppressed by the beat filter — no
   wasted GPU cycles
3. Narration is read aloud by the correct voice per character/NPC, streaming smoothly
4. Music shifts to match the narrative mood (combat starts, tension builds, calm returns)
5. Music ducks automatically when TTS is playing, then restores
6. Duplicate render requests are deduplicated by content hash
7. Speculative prerendering queues the next image while voice is still playing, reducing
   perceived latency
8. All media failures are non-fatal — the game continues with text-only fallback
