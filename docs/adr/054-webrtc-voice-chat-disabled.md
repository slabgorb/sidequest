# ADR-054: WebRTC Voice Chat (Disabled — Echo Feedback Loop)

> Retrospective — documents a decision already implemented in the codebase.

## Status
Accepted (historical — 2026-04 update)

> **Update (2026-04-11):** The "full implementation is preserved" claim below is
> no longer true. After TTS removal, the WebRTC voice chat files
> (`PeerMesh.ts`, `useVoiceChat.ts`, `LocalTranscriber.ts`, `useWhisper.ts`) and
> the entire `sidequest-ui/src/webrtc/` directory have been **deleted** from the
> UI repo. The echo-feedback motivation and the architectural rationale below
> remain as history. Any future voice chat work should start from a fresh ADR —
> the original echo problem would need to be re-analyzed against whatever new
> audio pipeline replaces the (also removed) Kokoro TTS output path.

## Context
Multiplayer SideQuest sessions need player-to-player voice communication. A `PeerMesh` WebRTC
implementation was built for this purpose. Simultaneously, a `LocalTranscriber` using Whisper
via WebGPU/WASM was implemented to allow voice input — players speaking actions rather than
typing them.

During integration testing, a closed-loop echo problem was discovered: TTS narration plays
through the system speakers, the microphone picks it up, Whisper transcribes it as player
input, and the narrator receives its own output as a new player action. The narrator then
responds to itself. The loop compounds with each exchange — narration fragments, context
bloats, and the session becomes incoherent within a few turns.

This is not a volume problem. Reducing TTS volume reduces but does not eliminate transcription.
The fix requires acoustic echo cancellation keyed on TTS playback state, hardware-level audio
routing, or input gating synchronized with TTS activity — none of which are trivially available
in a browser WebGPU context.

## Decision (original)
Voice chat and local transcription were originally disabled via a compile-time
constant rather than removed, on the theory that the WebRTC infrastructure was
correct and should be preserved against future re-enablement once echo
isolation was solved.

## What actually shipped (2026-04)
TTS (Kokoro) was removed from the system in April 2026, and with it went the
original motivation for preserving a disabled voice-chat path against a
future TTS-aware AEC solution. The WebRTC voice chat files were then deleted
outright:

- `sidequest-ui/src/webrtc/` — entire directory removed
- `PeerMesh.ts` — removed
- `useVoiceChat.ts` — removed
- `LocalTranscriber.ts` — removed
- `useWhisper.ts` — removed
- `VOICE_DISABLED` constant — removed

If voice chat returns, it should start from a fresh ADR built on top of
whatever the post-TTS audio pipeline looks like. The original echo-feedback
analysis below is retained as history only.

## Alternatives Considered

- **Remove the implementation** — rejected because the WebRTC infrastructure is correct and
  represents significant implementation work. The echo problem is an isolation failure, not
  a design failure. Removing it would destroy working infrastructure that will be re-enabled
  once echo cancellation is solved.

- **Push-to-talk with TTS mute** — viable mitigation, not yet implemented. Requires gating
  microphone activation on a button held while TTS is inactive. Reduces but may not eliminate
  echo with reverb.

- **Acoustic echo cancellation (AEC)** — the correct architectural fix. Browser AEC APIs
  exist (`echoCancellation: true` on `getUserMedia`) but do not reliably cancel TTS because
  TTS is rendered to an `AudioContext` rather than the physical speaker as far as the AEC
  reference signal is concerned. Needs investigation into loopback reference injection.

- **Headphone requirement** — would solve the physical echo but cannot be enforced in a
  browser context and breaks accessibility.

## Consequences

**Positive:**
- The echo feedback loop is fully prevented — no risk of sessions becoming incoherent due
  to narrator self-response.
- Working WebRTC infrastructure is preserved for re-enablement once echo isolation is solved.
- `useWhisper.ts` stub is explicit about why it returns empty — future maintainers have a
  clear path rather than a mystery.

**Negative:**
- Multiplayer voice communication is unavailable. Players must use external voice tools
  (Discord, etc.) for coordination.
- Voice input is unavailable. Players must type all actions.
- The disabled implementation creates maintenance surface — it must be kept compilable and
  conceptually current even while disabled.
- Any future re-enablement requires solving a non-trivial audio engineering problem in
  a browser WebGPU context before the feature can ship.
