---
id: 45
title: "Client Audio Engine"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [media-audio]
implementation-status: live
implementation-pointer: null
---

# ADR-045: Client Audio Engine

> Retrospective — documents a decision already implemented in the codebase.

> **Note (2026-04):** TTS/voice narration has been removed from the system.
> The Kokoro TTS daemon, voice channel, PCM streaming, and Ducker are no longer
> active. The audio engine now handles two streams: background music and SFX.
> The Web Audio API architecture and Crossfader remain as described.

## Context
The game client plays concurrent audio streams: background music (cinematic, pre-rendered .ogg files) and sound effects. These streams must mix and sequence correctly, and the whole system must respect browser autoplay policy (AudioContext requires a user gesture before it will produce sound).

HTML5 `<audio>` elements can't mix channels. Third-party libraries like Howler.js add unnecessary complexity. The audio system was built directly on the Web Audio API.

## Decision
A singleton `AudioEngine` owns a two-channel Web Audio graph: music → sfx, each channel with an independent gain node feeding a master gain node feeding the destination.

`Crossfader` manages music transitions: when a new track is requested, it overlaps the fade-out of the current track with the fade-in of the new one, avoiding the silence gap of a sequential stop/start.

The AudioContext is created inside the first user gesture handler (browser requirement). A visibility change listener resumes the context when the tab regains focus after backgrounding. Volume state persists to localStorage.

Implemented in `sidequest-ui/src/audio/AudioEngine.ts`, `Ducker.ts`, `Crossfader.ts`.

## Alternatives Considered

- **HTML5 Audio elements** — No mixing control, no programmatic gain, no channel routing. Cannot duck music under voice without platform-specific hacks.
- **Howler.js** — Mature library but adds unnecessary abstraction over Web Audio API for our use case.

## Consequences

**Positive:**
- Full mixing control: music and sfx are independently gained and routable.
- Crossfader produces seamless music transitions.
- No library dependency for core audio functionality.

**Negative:**
- AudioContext autoplay gate requires careful initialization sequencing; errors surface only at runtime in new browser versions.
- Two-channel graph is hand-wired — adding a third channel (e.g., ambient) requires manual graph surgery.
- Volume persistence in localStorage is lost in private browsing mode.

## Implementation status (2026-05-02)

Audited during the post-port hygiene sweep. The ADR's specified surface is
fully live; the 2026-04 TTS-removal subtraction (Ducker, voice channel, PCM
streaming) is complete with no dead code remaining.

**Live elements (file/line pointers):**

- Singleton AudioEngine — `sidequest-ui/src/audio/AudioEngine.ts:44`
  (`getInstance()` autoplay-gate pattern at lines 46–66).
- Two-channel Web Audio graph (music + sfx) — `channels: Record<ChannelName,
  GainNode>` at line 68; `masterGain` at line 69; volumes shape
  `{music, sfx, master}` at line 71.
- Crossfader — `sidequest-ui/src/audio/Crossfader.ts:3`, invoked from
  `playMusic` at `AudioEngine.ts:129`.
- AudioContext autoplay handling — `resume()` at line 97, `ensureResumed()`
  at line 108.
- Visibility-change resume — `registerVisibilityHandler()` at line 117 calls
  `ctx.resume()` when the tab returns to visible state from suspended.
- Volume persistence — `STORAGE_KEY` / `loadVolumes()` / `saveVolumes()` at
  lines 1–43, with silent-catch on private-browsing localStorage failure.
- App wiring — `sidequest-ui/src/hooks/useAudio.ts:9` consumes the
  singleton; per `sidequest-ui/CLAUDE.md`, audio is wired through `useAudio`
  at the App level rather than via a context provider.

**TTS-removal subtraction confirmed clean:** `grep -rn Ducker sidequest-ui/src/`
returns zero hits. The body's `Note (2026-04)` callout describes the current
state.

**Additive surface (not specified by this ADR, intentional):**

- `sidequest-ui/src/audio/AudioCache.ts` — caches decoded `AudioBuffer`
  instances to avoid redundant fetch + decode. Held at `AudioEngine.ts:74`,
  consulted at `playMusic` line 130. Optimization that landed after the ADR.
- `sidequest-ui/src/hooks/useAudioCue.ts` — convenience hook for SFX cues.
  Routes through the unified mixer channels per its own header comment;
  does not bypass the AudioEngine.

Neither is part of the ADR's scope; both are listed here so future readers
do not flag them as drift.
