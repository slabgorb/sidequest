---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-23: Solo narration streaming — wire messages.stream into existing UI delta path

## Business Context

On the default ADR-101 Anthropic SDK backend, solo narration arrives as one big
block at end-of-turn: the player submits, then stares at a stall for several seconds
until the entire narration card appears at once. This is the worst kind of wait for
the playgroup — Alex (slow reader/typist) and Keith-as-player both experience dead
air with no signal that the narrator is working. The UI **already has a complete
token-by-token delta-rendering path** — `streamingNarration.ts` (a reducer that
accumulates `narration.delta` chunks per `turn_id` and renders `chunks.join("")`
until the canonical `NARRATION` message lands) wired into `GameStateProvider.tsx`.
The server **already has** `broadcast_delta` (`sidequest/server/emitters.py`) and a
`NarrationDelta` / `NarrationDeltaPayload` protocol message. What is missing is the
connection on the **SDK tooling path**: the default narrator backend
(`AnthropicSdkClient.complete_with_tools`) runs the tool loop without streaming text
deltas out, so the existing UI delta path never receives chunks in solo play.

This is a textbook "Wire Up What Exists" story (CLAUDE.md): do not reinvent a
streaming renderer or a new message type. Wire the Anthropic SDK `messages.stream`
(or the existing `on_text_delta` callback already threaded into
`complete_with_tools`) into `broadcast_delta` so the prose tokens fan out to the
client, where the already-built reducer renders them incrementally.

## Technical Guardrails

**Server — the SDK tooling path (the producer-shaped hole):**
- `sidequest/agents/anthropic_sdk_client.py` — `complete_with_tools` (line ~281)
  ALREADY accepts an `on_text_delta: Callable[[str], None] | None` parameter
  (line ~292) and ALREADY invokes it: `if on_text_delta is not None and text:
  on_text_delta(text)` (lines ~530-531). **The callback hook exists** but the live
  SDK call is non-streaming today (`self._sdk.messages.create(...)`, line ~357) —
  `text` is extracted from the *completed* response, so `on_text_delta` fires once
  per iteration with whole blocks, not token deltas. The work: route the SDK call
  through `messages.stream` (or `messages.create(stream=True)`) and call
  `on_text_delta` on each `text_delta` event for true token-by-token output.
- `sidequest/agents/orchestrator.py` — `run_narration_turn` (line ~2800) routes the
  default (tooling) backend to `_run_narration_turn_sdk` (line ~2840-2841), NOT the
  legacy `_run_narration_turn_streaming` path (which asserts a non-tooling client
  and is `claude -p`-only). The existing inline comment (lines ~2829-2839) notes
  "SDK streaming is Phase D Task 7 and is NOT yet implemented." **This story is that
  Task 7 for solo.** The `room` parameter is already threaded into
  `run_narration_turn` for delta fan-out.

**Server — the delta emitter (already built, reuse it):**
- `sidequest/server/emitters.py` — `broadcast_delta` (line ~973) constructs a
  `NarrationDelta(payload=NarrationDeltaPayload(...))` and broadcasts to the room.
  Wire the `on_text_delta` callback to call this. `turn_id` must be stamped so the
  UI reducer can route the chunk.
- `sidequest/protocol/messages.py` — `NarrationDelta` (`kind: "narration.delta"`),
  `NarrationDeltaPayload` (line ~289) — "Ephemeral streaming delta — broadcast to
  all sockets, NOT event-sourced." Do not change the wire shape; the UI already
  parses it.

**UI — the delta render path (already built, do NOT reinvent):**
- `sidequest-ui/src/providers/streamingNarration.ts` — `reduceStreamingNarration`
  reducer: handles `narration.delta` (accumulates `chunks`) and the canonical
  `NARRATION` message (sets `canonical`, closes the active turn). Display rule:
  `displayTextForTurn` returns `canonical ?? chunks.join("")` (line ~137).
  Late-delta protection already exists (deltas after canonical are discarded).
- `sidequest-ui/src/providers/GameStateProvider.tsx` — already imports
  `reduceStreamingNarration`, `displayTextForTurn`, `initialStreamingState` (lines
  4-8) and holds `streamingNarrationState` (line ~187) plus `dispatchStreamingAction`
  (line ~88). `sidequest-ui/src/types/payloads.ts` already defines `NarrationDelta`,
  `NarrationDeltaPayload`, and the `isNarrationDelta` type guard (line ~656).
- Verify the WebSocket message intake actually routes an incoming
  `narration.delta` message into `dispatchStreamingAction`, and that a narration
  component renders via `displayTextForTurn` for the active turn. If a wiring gap
  exists between "reducer exists" and "reducer is fed live messages," closing it is
  in scope.

**Do NOT touch:** the non-tooling `_run_narration_turn_streaming` (`claude -p`)
path, the canonical `NARRATION` end-of-turn message contract, footnotes/state-delta
extraction, or the MP fan-out perception firewall (ADR-104/105 — this story is solo).

## Scope Boundaries

**In scope:**
- Route the SDK narrator call (`complete_with_tools`) through `messages.stream` so
  `on_text_delta` fires on real token deltas.
- Wire `on_text_delta` → `broadcast_delta` so `NarrationDelta` messages fan out
  during the turn, stamped with the turn's `turn_id`.
- Ensure the UI feeds incoming `narration.delta` into the existing reducer and
  renders incrementally; the canonical `NARRATION` still closes the turn.

**Out of scope:**
- MP streaming / per-recipient POV-swapped deltas and perception redaction of
  streamed prose (solo only this story).
- Streaming tool-use blocks or footnotes; only PART-1 prose streams (the
  `NarrationDeltaPayload` docstring already states "only PART-1 prose ships live").
- Any new message type or new UI component — the reducer and payload types exist.
- The legacy `claude -p` streaming path.

## AC Context

**AC1 — streamed deltas appear incrementally.** With the SDK backend, a solo
narration turn fans out multiple `NarrationDelta` messages (`kind: "narration.delta"`)
for one `turn_id` before the canonical `NARRATION`. Server test: drive
`complete_with_tools` with a mocked streaming SDK response yielding N `text_delta`
events, assert `on_text_delta` is called N times and (wired through `broadcast_delta`)
N `NarrationDelta` messages broadcast to the room, each carrying the turn's
`turn_id`. UI test (vitest): feed the reducer the N deltas then the canonical
message; assert `displayTextForTurn(turn_id)` returns the joined chunks before
canonical and the canonical text after.

**AC2 — non-streaming path unaffected.** When `on_text_delta` is `None` (or for the
`claude -p` non-tooling path), behavior is byte-identical to today: one canonical
`NARRATION`, no deltas. Test: run the SDK path without a delta sink wired and assert
no `NarrationDelta` is broadcast and the canonical result text is unchanged.

**AC3 — canonical closes the turn / late deltas dropped.** After the canonical
`NARRATION` lands for a `turn_id`, any straggler delta for that turn is discarded
(the reducer already enforces this — assert it with a delta-after-canonical test).

**Wiring (required):** an end-to-end-ish test that drives the *real*
`broadcast_delta` from the `on_text_delta` callback (not a standalone unit of the
reducer) and asserts a typed `NarrationDelta` message reaches the room broadcast —
proving the server half is connected, not just defined.

## Interaction Patterns

Player submits in solo → narrator SDK call streams → prose tokens fan out as
`narration.delta` → narration card fills in token-by-token (via
`displayTextForTurn`) → end-of-stream canonical `NARRATION` replaces accumulated
chunks and closes the active turn. The stall-fallback interstitial
(`activeTurnStartedAt`, 5s) in the existing reducer remains the safety net for a
slow first token.

## Assumptions

- The Anthropic SDK in use exposes `messages.stream` / `messages.create(stream=True)`
  with `text_delta` events under the tool-use loop (the SDK is the ADR-101 default;
  the `claude-api` skill documents the streaming + tool-use combination).
- The existing `on_text_delta` callback contract is the intended seam (the parameter
  and call site already exist in `complete_with_tools`); this story makes it carry
  real token deltas rather than per-iteration whole-block text.
- `turn_id` is available to stamp on each delta at the `broadcast_delta` call site
  (the canonical `NARRATION` does not carry `turn_id` on the wire, but the reducer
  routes it to the active streaming turn — so deltas MUST carry `turn_id`).
- Tests mock the SDK streaming response; no live `ANTHROPIC_API_KEY` is required
  (mirrors how the orchestrator/intent-router are stubbed in test conftest).

If the SDK's streaming-with-tools shape differs from `on_text_delta`'s simple
`(str) -> None` contract (e.g. deltas interleave with tool_use blocks needing
ordering), log a Design Deviation and notify SM before reshaping the callback.
