# ADR-076: Narration Protocol Collapse Post-TTS Removal

**Status:** Proposed
**Date:** 2026-04-10
**Deciders:** Keith
**Relates to:** ADR-065 (Protocol Message Decomposition — proposes file reorganization, unexecuted)

## Context

The SideQuest narration pipeline originally used a three-state streaming protocol
designed around Kokoro TTS playback:

| Message | Original Role |
|---------|---------------|
| `Narration` | Full narration text + optional state delta — sent at the start of a turn so the UI could match incoming audio chunks to their source text |
| `NarrationChunk` | A single segment of narration text, paired with a binary voice frame arriving on the same WebSocket — the UI revealed the chunk's text at the moment its matching audio started playing |
| `NarrationEnd` | Terminal marker for the stream — signalled "all chunks delivered, it is safe to commit the final state delta and release the UI buffer" |

Binary WebSocket frames (PCM `s16le` voice audio from Kokoro) arrived interleaved
with the `NarrationChunk` text messages. The UI's `narrationBufferRef` in `App.tsx`
maintained a `chunks: GameMessage[]` queue that was drained one entry per binary
frame, producing the synchronized text-and-audio reveal.

**TTS has been removed from the server.** The Kokoro subprocess integration, the
`TtsStartPayload`, and the `TtsChunkPayload` variants referenced in ADR-065 are
all gone. Binary voice frames are no longer sent — a grep for `Message::Binary`
or any equivalent binary send site in `sidequest-api/crates/sidequest-server`
returns zero production hits (the only `Binary` mention in `main.rs` refers to
ADR-059 tool binaries, not WebSocket frames). The `NarrationChunk` variant has
**zero production construction sites** in the server and is referenced only by a
serde round-trip test in `tests.rs`. In the UI, `NarrationChunkMessage` is not
in the `TypedGameMessage` union, there is no type guard for it, and nothing
writes to `buf.chunks` in `App.tsx` — the field is drained in two places and
filled in none.

Meanwhile, `NarrationEnd` is emitted from **eight production call sites** across
`dispatch/response.rs`, `dispatch/aside.rs`, `dispatch/slash.rs`,
`dispatch/connect.rs`, `dispatch/session_sync.rs`, `dispatch/catch_up.rs`,
`dispatch/mod.rs`, and matched in `lib.rs`. The UI uses it to flush the
narration buffer and commit accumulated state. It found a second life as a
turn-completion marker, even though its name and its doc comment still describe
the stream-terminator role.

This leaves three distinct problems:

1. **A dead protocol variant** (`NarrationChunk`) that survives in both type
   systems despite zero callers.
2. **A partially-dead UI subsystem** — roughly 60% of the narration buffer code
   in `App.tsx` exists to synchronize text with binary voice frames that will
   never arrive.
3. **Documentation rot** in `sidequest-game/src/prerender.rs` and
   `sidequest-server/src/extraction.rs`, where doc comments describe behavior
   in terms of TTS playback windows that no longer exist.

## Decision

**Collapse the narration streaming protocol to its steady-state post-TTS shape,
update all documentation to reflect current behavior, and remove all
TTS-specific UI plumbing in a single atomic change.**

### Protocol Layer

Remove `GameMessage::NarrationChunk` and `NarrationChunkPayload` from
`sidequest-protocol/src/message.rs`. Delete the corresponding serde round-trip
test in `tests.rs`. Delete `NarrationChunkPayload` from
`sidequest-ui/src/types/payloads.ts`.

### Narration Flow, Formalized

After this change, the narration protocol has exactly two messages:

| Message | Role |
|---------|------|
| `Narration` | Full narration text plus any immediate footnotes. May or may not carry a `StateDelta`. |
| `NarrationEnd` | Turn-completion marker. Carries the final `StateDelta` when one exists. Signals the UI to flush its narration buffer and commit accumulated state atomically. |

`NarrationEnd` is retained because it does real work: the UI buffer pairs a
`Narration` with its corresponding `NarrationEnd` so that a state delta arriving
at end-of-turn applies atomically with the narration text, not as a separate
render cycle that could cause visible out-of-order updates. The eight production
senders do not need to change. Only the doc comment on the variant needs
updating to describe its current semantics.

### UI Narration Buffer Cleanup

In `sidequest-ui/src/App.tsx:180-264`:

1. Remove `chunks: GameMessage[]` from `narrationBufferRef`.
2. Remove `watchdogTimer` from `narrationBufferRef`.
3. Delete `handleBinaryMessage` entirely. Unregister it from the WebSocket
   binary-handler hook.
4. Remove `isVoiceAudioFrame` and `decodeVoiceFrame` imports if they have no
   other consumers; audit the hook/audio layer before deletion.
5. Simplify `flushNarrationBuffer` to only handle `narration` and
   `narrationEnd`.
6. Rewrite the block comment on lines 180–183 to describe what the buffer
   actually does now: "Buffer a `Narration` until its paired `NarrationEnd`
   arrives, then flush both atomically so the `StateDelta` applies in the same
   React commit as the narration text."

Note: `useAudio`, `audio.engine.playVoicePCM`, and `audio.engine.playVoice` are
**out of scope** for this ADR. They may have other callers (e.g. SFX, music)
and their dead-code status is not part of this decision. If they turn out to be
orphaned, that is a separate ADR.

### Documentation Cleanup

`sidequest-game/src/prerender.rs`:

- Line 1: `//! Speculative prerendering — queue image generation during voice playback.`
- Line 3: `//! While TTS narration is playing (5–15 seconds), the [\`PrerenderScheduler\`]...`
- Line 97: `/// Schedules speculative image renders during TTS playback windows.`

The scheduler logic itself is correct and does not depend on TTS timing — it
queues against turn boundaries, not audio durations. Only the doc comments need
to be rewritten to describe the current behavior: "Queue speculative image
renders during the gap between narration turns, whatever its duration, to
amortize rendering latency across the player's reading time."

`sidequest-server/src/extraction.rs`:

- Line 4: `//! TTS-clean text, and audio cue conversion.`
- Line 155: `// These must be removed before the narration reaches the client or TTS pipeline.`

The cleanup logic is still valuable for visual display — stripping stage
directions, normalizing punctuation, extracting audio cues. Only the doc
comments need to shift from "TTS-clean" framing to "narration display cleanup"
framing.

### Daemon Client Types

Audit `sidequest-api/crates/sidequest-daemon-client/src/types.rs` for any
`Tts*` or `Voice*` synthesis request/response types that have no remaining
callers. Delete them. This is a small surgical pass and should be contained to
the same PR so the daemon-client crate does not temporarily expose types the
protocol can no longer carry.

### Cross-Repo Wiring Diagram

`docs/wiring-diagrams.md` references `NarrationChunk` in the narration flow
diagram. Update to remove the chunk arrow and reflect the simplified two-
message flow.

## Alternatives Considered

### Leave `NarrationChunk` in place "in case TTS comes back"

Rejected. The project's `No Stubbing` rule (CLAUDE.md) is explicit: "If a
feature isn't being implemented now, don't leave empty shells for it. Dead code
is worse than no code." Keeping a protocol variant with zero construction sites
violates the rule directly. If TTS is reintroduced later, it will almost
certainly use a different streaming shape (e.g. a single `VoiceTrack` message
with a URL reference, or a post-narration audio job posted separately like
images are), so preserving the exact old shape is not insurance against
anything.

### Also remove `NarrationEnd` and fold its role into `Narration`

Tempting but rejected. `NarrationEnd` has eight production senders, and its
payload carries a `StateDelta` that the server does not always have at
`Narration` emission time — some senders emit `Narration` first, then do
further work (tool calls, state reconciliation), then emit `NarrationEnd` with
the final delta. Collapsing the two would require rearranging eight dispatch
call sites to compute the state delta upfront. Out of scope for this cleanup.
If a future simplification pass wants to pursue this, it deserves its own ADR.

### Split into multiple stories

Rejected. The project has a well-documented pattern of creating wiring gaps
when connected cleanups are split across stories. Removing the protocol
variant without simultaneously removing its dead UI buffer plumbing would leave
the UI handling a discriminated union member that the protocol no longer
defines — TypeScript would silently allow this because the corresponding
`NarrationChunkMessage` type was never in the union in the first place, which
is precisely how the half-wired state came to exist. A single atomic PR is the
only safe delivery shape.

### Supersede ADR-065

Rejected. ADR-065 is about file organization (splitting `message.rs` into a
`message/` directory). Its decision is orthogonal to what this ADR addresses
(removing dead content from the protocol). ADR-065 remains Proposed and
unexecuted and can be picked up independently. This ADR only **relates to**
ADR-065 because they touch the same file; if ADR-065 is later executed, that
story will need to drop `TtsStartPayload`, `TtsChunkPayload`, and
`NarrationChunkPayload` from its module layout, since all three are either
gone or being removed by this ADR.

## Consequences

### Positive

- One less protocol variant to reason about. `GameMessage` drops from 30 to 29
  variants. Every new maintainer no longer has to trace `NarrationChunk`
  through the dispatch layer only to discover it is unreachable.
- UI narration buffer becomes proportional to its job. A reader unfamiliar
  with SideQuest's history no longer wonders why `buf.chunks` exists and what
  fills it.
- Documentation in `prerender.rs` and `extraction.rs` stops lying about TTS.
  This matters for future Architects and Devs reading those modules cold.
- Re-establishes CLAUDE.md's `No Stubbing` principle on a protocol that had
  drifted away from it. Dead variants and dead branches are harder to remove
  the longer they sit.
- The new two-message narration shape is documentable in a single table,
  which helps the next ADR that touches narration (verbosity, vocabulary,
  voice reintroduction, etc.) start from a clean baseline.

### Negative

- Breaking protocol change in the literal sense: any client connecting to the
  server that expects to receive a `NarrationChunk` message will now never
  receive one. In practice there are no such clients (the only UI is in this
  repo, and it already does not handle the variant), so the "break" is on
  paper only. No schema version bump is warranted.
- Touches multiple repos in one PR: `sidequest-api`, `sidequest-ui`, and
  `orc-quest`. This is a modest coordination cost, handled by gitflow PR
  discipline (develop for subrepos, main for the orchestrator).

### Risks

- **Risk:** Deleting `isVoiceAudioFrame` / `decodeVoiceFrame` without auditing
  their other consumers could break an unrelated audio path. *Mitigation:* the
  Dev story explicitly calls for a grep of all callers before deletion; if
  other consumers exist, leave the helpers in place and only remove the
  `handleBinaryMessage` call site.
- **Risk:** A reviewer or future Architect may read this ADR and assume TTS
  was removed in error and should be restored. *Mitigation:* this ADR
  intentionally does not justify the TTS removal itself — that decision is
  already made. It only records the protocol consequences. If TTS comes back,
  a future ADR can introduce a new (likely different-shaped) voice delivery
  protocol from a clean baseline.
- **Risk:** A sibling story or in-flight PR may reference `NarrationChunk` in
  generated code, scenario fixtures, or test data. *Mitigation:* the wiring
  check at story exit must grep both repos for `NarrationChunk` /
  `NarrationChunkPayload` and confirm zero hits. The protocol crate's `cargo
  check` will catch any broken imports.

## Implementation Gate

This ADR becomes **Accepted** only when:

1. The Dev story implementing the collapse has merged to `develop` on both
   `sidequest-api` and `sidequest-ui`.
2. A wiring check confirms zero production references to `NarrationChunk`,
   `NarrationChunkPayload`, or `handleBinaryMessage` in either repo.
3. `just check-all` passes on the orchestrator repo.
4. A manual playtest confirms that narration still reveals correctly and
   state deltas (HP changes, inventory changes, location changes) still
   apply atomically with their narration text, not as a second render.

Until all four gates pass, the ADR remains Proposed.
