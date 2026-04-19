---
story_id: "4-8"
jira_key: "none"
epic: "4"
workflow: "tdd"
---
# Story 4-8: TTS streaming — stream synthesized audio chunks to client via WebSocket

## Story Details
- **ID:** 4-8
- **Jira Key:** none (personal project)
- **Epic:** 4 — Media Integration
- **Workflow:** tdd
- **Stack Parent:** 4-7 (feat/4-7-tts-text-segmentation)

## Workflow Tracking
**Workflow:** tdd
**Phase:** review
**Phase Started:** 2026-03-27T08:43:13Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-26T00:00:00Z | 2026-03-27T08:20:47Z | 32h 20m |
| red | 2026-03-27T08:20:47Z | 2026-03-27T08:38:28Z | 17m 41s |
| green | 2026-03-27T08:38:28Z | 2026-03-27T08:41:48Z | 3m 20s |
| spec-check | 2026-03-27T08:41:48Z | 2026-03-27T08:43:13Z | 1m 25s |
| verify | 2026-03-27T08:43:13Z | 2026-03-27T08:43:13Z | 0s |
| review | 2026-03-27T08:43:13Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): DaemonClient has no TTS `synthesize()` method yet. Affects `crates/sidequest-daemon-client/src/client.rs` (needs synthesize endpoint). *Found by TEA during test design.*
- **Gap** (non-blocking): No `base64` crate was in workspace deps — added to sidequest-game. Affects `crates/sidequest-game/Cargo.toml`. *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### TEA (test design)
- **Used TtsSynthesizer trait instead of DaemonClient directly**
  - Spec source: context-story-4-8.md, Technical Approach
  - Spec text: "let daemon = self.daemon.clone()" — uses DaemonClient directly
  - Implementation: Tests use a TtsSynthesizer trait for DI, with MockSynthesizer/FailingSynthesizer/DeadSynthesizer test doubles
  - Rationale: Same Strategy pattern used in 8-6 (PerceptionRewriter). Keeps tests deterministic, no daemon dependency. DaemonClient will implement the trait.
  - Severity: minor
  - Forward impact: none — Dev implements ClaudeSynthesizer (or DaemonSynthesizer) wrapping DaemonClient

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5pt TDD story with 10 ACs for TTS streaming pipeline

**Test Files:**
- `crates/sidequest-game/tests/tts_stream_story_4_8_tests.rs` — 20 tests covering all 10 ACs
- `crates/sidequest-game/src/tts_stream.rs` — Types + stub stream() method

**Tests Written:** 20 tests covering 10 ACs
**Status:** RED (15 failing, 5 passing — types compile, stream() is todo!())

**Self-check:** All tests have meaningful assertions (assert_eq on message types, indices, speakers, base64 decode, is_last flags). No vacuous assertions found.

**Handoff:** To Dev (Winchester) for implementation

### Dev (implementation)
- No upstream findings during implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/tts_stream.rs` — Implemented `TtsStreamer::stream()`: TtsStart → synthesize+base64+TtsChunk per segment → TtsEnd, with pause hints and graceful segment-level failure handling

**Tests:** 20/20 passing (GREEN)
**Branch:** feat/4-8-tts-streaming (pushed)

**Handoff:** To next phase (verify or review)

## Sm Assessment

**Story 4-8: TTS streaming** — 5pt TDD story in Epic 4 (Media Integration).

**Scope:** Stream synthesized audio chunks from the Python daemon (Kokoro/Piper TTS) to the React client via WebSocket binary frames. Builds on 4-7 (TTS text segmentation) which breaks narration into streamable sentences.

**Approach:** TDD workflow in sidequest-api (Rust). The server receives TTS audio from the daemon, chunks it, and broadcasts binary WebSocket frames to connected clients. The UI already handles binary frames via `onBinaryMessage` in `useGameSocket`.

**Dependencies:** 4-7 (TTS segmentation) complete. Daemon TTS endpoint exists in sidequest-daemon.

**Repos:** sidequest-api (Rust backend).

**Routing:** TDD phased — TEA for RED phase.