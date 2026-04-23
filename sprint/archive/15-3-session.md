---
story_id: "15-3"
epic: "15"
workflow: "tdd"
repo: "sidequest-ui"
branch: "feat/15-3-voice-mic-tts-feedback-loop"
---

# Story 15-3: Voice/mic architecture — solve TTS feedback loop before re-enabling

## Story Details
- **ID:** 15-3
- **Epic:** 15 (Playtest Debt Cleanup — Stubs, Dead Code, Disabled Features)
- **Points:** 5
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** sidequest-ui
- **Branch:** feat/15-3-voice-mic-tts-feedback-loop

## Problem Statement

Voice input is disabled across 4 hooks/components due to a critical feedback loop:

1. **useVoiceChat.ts** — VOICE_DISABLED = true (line 24)
2. **usePushToTalk.ts** — enabled = false (line 35), _disabled = true (line 33)
3. **useWhisper.ts** — DISABLED = true
4. **InputBar.tsx** — wired to disable mic UI when voice is off

**Root cause:** Microphone captures TTS audio playback and feeds it back as player input, fragmenting the narration with echo/feedback loops.

**Current architecture gaps:**
- No echo cancellation strategy (MediaConstraints has `echoCancellation: true` but it's disabled upstream by the VOICE_DISABLED flag)
- No output device exclusion (use `audioDeviceId` with speaker-only output)
- No TTS-aware mic gating (mute mic during TTS playback, unmute after)

## Scope: TDD Approach

This story requires implementing one or more of these three architectural solutions:

### Option 1: TTS-Aware Mic Gating (Recommended)
- Add mic muting/unmuting via the VoiceChatHandle interface
- Update AudioEngine to expose playback lifecycle hooks (onVoiceStart, onVoiceEnd)
- Sync usePushToTalk and useVoiceChat to mute mic during TTS segments
- **Simplest to test:** binary on/off state

### Option 2: Echo Cancellation + Audio Context Tuning
- Enable echoCancellation: true in getUserMedia constraints (already written, just gated)
- Verify Web Audio API echo cancellation properties (processor detection)
- Test with simulated feedback loops

### Option 3: Output Device Exclusion
- Use audioDeviceId in AudioContext creation and getUserMedia
- Enumerate audio devices, identify speaker vs mic
- Route TTS output to speaker device only
- **Most robust but browser support varies**

## Acceptance Criteria

1. **Remove all four kill switches** (VOICE_DISABLED, enabled = false, DISABLED = true)
2. **Implement echo cancellation or mic gating** (at least one solution)
3. **All hooks pass updated tests** that verify:
   - Mic starts/stops correctly
   - TTS playback does not trigger feedback loops
   - Muting/unmuting works end-to-end
4. **Integration test:** Play TTS, verify mic doesn't capture it
5. **No regression:** Existing voice features (WebRTC mesh, PTT transcription) work

## Discovery: Current Implementation

### useVoiceChat.ts
- Creates PeerMesh for WebRTC peer-to-peer voice
- Has muteOutgoing/unmuteOutgoing methods (used by usePushToTalk for gating)
- Gated by VOICE_DISABLED flag

### usePushToTalk.ts
- Records audio from mic, transcribes via Whisper API
- Has logic to call voiceChat.muteOutgoing/unmuteOutgoing around recording
- Gated by enabled = false (hardcoded)

### AudioEngine.ts
- Controls three channels: music, sfx, voice (TTS)
- Has voiceChain promise for sequential TTS playback
- **Missing:** No hooks to notify consumers when voice playback starts/ends

### InputBar.tsx
- Renders mic button and PTT UI
- micEnabled prop gates visibility of voice controls

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-05T20:30:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-05T20:30:00Z | - | - |

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
