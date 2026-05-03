# Narration Streaming — Design

**Date:** 2026-05-02
**Status:** Draft (architect)
**Author:** The Man in Black (architect persona)
**Audience:** Dev, TEA, Reviewer
**Companion ADRs:** ADR-038 (WebSocket transport), ADR-066 (persistent narrator sessions), ADR-067 (unified narrator agent), ADR-026 (client-side state mirror), ADR-090 (OTEL dashboard)

---

## 1. Problem

Narration turns regularly run 30–60+ seconds (p50 ~33s, p95 > 60s in current OTEL telemetry). The player sees a spinner for the entire duration: nothing, then a wall of text. Across the playgroup this consistently breaks attention — Alex (slower reader) and Sebastien (mechanics-first) feel the dead time most, but every player loses the table's narrative momentum.

The LLM cost is the floor: a single Claude CLI call generating a meaty narration turn cannot reasonably finish in under 15–20 seconds, and dramatic turns will exceed 60s. We cannot make the LLM faster. We can stop hiding its work.

**Goal:** Convert the spinner into reading time. First sentence visible at 2–3 seconds (TTFT). Full block lands at the same total wall-clock as today, but the player has been engaged the whole time.

## 2. Constraints — Discovered During Design

Three architectural facts shape the design:

1. **The narrator's response already has a clean boundary.** The prompt in `sidequest-server/sidequest/agents/narrator.py:80-93` requires PART 1 prose followed by PART 2: a fenced JSON block labeled `game_patch`. The labeled fence is unambiguous and is the natural split point for streaming.

2. **`claude_client.py` is deliberately synchronous today.** It uses `--output-format json` + `proc.communicate()` and declares `supports_streaming=False`. The Claude CLI itself supports `--output-format stream-json`; the wrapper does not consume it. The capability flag suggests prior intent to add streaming that never landed.

3. **The perception rewriter operates on `spans[]` with `kind` tags, but the narrator does not currently emit kind-tagged spans.** `perception_rewriter.py:rewrite_for_recipient` is effectively a no-op for narration today (the `spans` field is absent or empty). G10 LLM re-voicing is explicitly deferred per the module's own docstring. **This means broadcasting unfiltered prose deltas to all players is correct today.** When G10 ships, deltas-vs-canonical reconciliation needs a redesign; until then, this design is correct.

## 3. Goals & Non-Goals

### Goals

- First-token-time (TTFT) of 1–3s from prompt submission, observable in OTEL.
- Player sees prose chunks arriving at LLM-generation pace, not buffered to end.
- The canonical event-sourced record (EventLog, projection cache, perception filter) is **byte-identical** to today. Reconnect/replay/audit are unaffected.
- The change is observable end-to-end: GM panel can prove streaming is happening per turn.
- The change is feature-flagged so it can be disabled without code changes.

### Non-Goals

- **G10 LLM re-voicing of narration per-recipient.** Deferred. When it ships, this design is revisited.
- **Kind-tagged span emission from the narrator.** The `spans[]` infrastructure is for a future feature; this design ships before it.
- **Two-call narrator architecture (narrate + extract).** Rejected: doubles cold-start cost, conflicts with ADR-067 (unified narrator session).
- **Streaming for non-narrator agents** (lethality_arbiter, encounter_render, local_dm). They are short or off the player's wait path.
- **Coalescing backpressure.** Defer until OTEL shows it's needed.
- **Visual chunking / typewriter pacing.** UX polish; defer.

## 4. Architecture Overview

### Today (synchronous)

```
narrator.respond()
  └─→ claude_client.send_with_session(prompt)
        └─→ spawn `claude -p --output-format json`
            └─→ proc.communicate()        ← BLOCKS 30–60s
            └─→ parse JSON envelope
        └─→ returns ClaudeResponse
  └─→ narrator splits prose | game_patch from text
  └─→ emit_event(narration_complete)
        └─→ projection_filter
        └─→ perception_rewriter
        └─→ WS fan-out (per-player filtered)

Player sees: [spinner ........................ full block]
```

### Proposed (streaming)

```
narrator.respond()
  └─→ claude_client.send_stream(prompt)   ← async iterator
        └─→ spawn `claude -p --output-format stream-json`
        └─→ async for line in proc.stdout:
              └─→ yield TextDelta(chunk)
  └─→ narrator drives StreamFenceParser
        ├─ state = PROSE
        │   └─→ broadcast `narration.delta` WS frame
        │       (ephemeral, no event-sourcing, all sockets)
        ├─ detect "\n```game_patch\n"
        │   └─→ state = JSON_BUFFERING (stop emitting deltas)
        ├─ accumulate JSON in buffer
        └─ on stream EOS:
              └─→ parse buffered JSON
              └─→ emit_event(narration_complete, game_patch)  ← UNCHANGED
                    └─→ projection_filter + perception_rewriter
                    └─→ WS fan-out (canonical, per-player filtered)

Player sees: [thinking 1–2s] [first sentence] [chunks flowing in] [final frame at EOS]
```

### Load-Bearing Invariants

- **The canonical event stream is unchanged.** Every event-sourced record, projection-cache row, and per-recipient projection that exists today still gets written exactly once, at end-of-turn.
- **Deltas are ephemeral.** They go on the wire only. They are not in the EventLog, not in the projection cache, not replayable on reconnect.
- **The frontend reconciles to canonical at EOS.** The accumulated delta buffer is replaced with the canonical `narration.payload.text` when the terminal event arrives.

### Where Each Change Lives

| Layer | New | Changed | Unchanged |
|---|---|---|---|
| `claude_client.py` | `send_stream()`, `StreamEvent` types, NDJSON consumer | `_run_subprocess` factored to share spawn with streaming variant; `supports_streaming=True` for streaming path | Token accounting, OTEL parent span shape, error types |
| `narrator/stream_fence.py` (new) | `StreamFenceParser`, `FenceParseResult` | — | — |
| `narrator.py` | streaming branch in `respond()` | post-EOS logic now reads `FenceParseResult` instead of splitting `ClaudeResponse.text` | Prompt template, ADR-067 unified session model |
| `server/emitters.py` | `broadcast_delta()` helper | — | `emit_event()` and full projection / rewrite / fan-out path |
| Server WS protocol | `narration.delta` message type | — | All other message types |
| `sidequest-ui` | delta accumulator in state mirror, narration-screen incremental render | WS client handler dispatches new message kind | Final-frame rendering, history view |
| OTEL | New spans: `narrator.stream.start`, `.first_token`, `.fence_detected`, `.delta`, `.complete`, `.error`, `.cancelled` | `agent_call_session_span` gains `ttft_seconds`, `terminal_kind` attributes | All other spans |

## 5. Component Design

### 5.1 `claude_client.send_stream()`

```python
async def send_stream(
    self,
    prompt: str,
    model: str,
    session_id: str | None = None,
    system_prompt: str | None = None,
    allowed_tools: list[str] | None = None,
    env_vars: dict[str, str] | None = None,
) -> AsyncIterator[StreamEvent]:
    """Execute a persistent session call with streaming output.

    Spawns claude with --output-format stream-json, parses NDJSON line-by-line
    from stdout, and yields events as they arrive. The iterator's terminal
    event is always StreamComplete (success) or StreamError (failure).
    Cancelling the iterator (aclose) terminates the subprocess.
    """
```

Mirrors `send_with_session()` parameter-for-parameter so the narrator can swap call sites without re-plumbing session/model/tool wiring.

### 5.2 Stream Event Types

```python
@dataclass(frozen=True, slots=True)
class StreamEvent:
    """Base for events yielded from send_stream()."""

@dataclass(frozen=True, slots=True)
class TextDelta(StreamEvent):
    """An incremental chunk of assistant prose. Concatenating all
    TextDelta.text values in order yields the final response text."""
    text: str

@dataclass(frozen=True, slots=True)
class StreamComplete(StreamEvent):
    """Terminal event on success."""
    full_text: str
    input_tokens: int | None
    output_tokens: int | None
    cache_creation_input_tokens: int | None
    cache_read_input_tokens: int | None
    session_id: str | None
    elapsed_seconds: float

@dataclass(frozen=True, slots=True)
class StreamError(StreamEvent):
    """Terminal event on failure. Stream cannot continue."""
    kind: Literal["timeout", "subprocess_failed", "parse_error", "empty"]
    elapsed_seconds: float
    partial_text: str
    detail: str
    exit_code: int | None
```

**Invariants:** the iterator yields zero or more `TextDelta` events, then **exactly one** `StreamComplete` or **exactly one** `StreamError`. Never both, never neither.

### 5.3 NDJSON Consumer

`claude -p --output-format stream-json` emits NDJSON — one JSON object per stdout line. Two known event categories matter:

- **Text delta events** (high-frequency): each carries a chunk of generated text. Yield as `TextDelta(text=chunk)`.
- **Terminal/result event** (one at end-of-stream): carries usage tallies, session_id, and (redundantly) full text. Yield as `StreamComplete(...)`.

Unknown event kinds are ignored (forward-compatibility — Claude CLI may add new kinds).

The exact JSON field paths inside each event kind are CLI-version-dependent. The implementation should verify the precise shape against current Claude CLI output (one-off `claude -p --output-format stream-json` invocation captured to a file) before finalizing the parser; the design treats those field paths as an implementation contract, not a design constraint.

Reader is straightforward asyncio:

```python
async for raw_line in proc.stdout:
    line = raw_line.decode("utf-8").strip()
    if not line:
        continue
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        logger.warning("claude_cli.stream.malformed_line line=%r", line[:200])
        continue
    # dispatch event by type, yield TextDelta or StreamComplete
```

### 5.4 Internal Refactor

`_run_subprocess()` splits into:

| Method | Responsibility |
|---|---|
| `_spawn_subprocess(args, env, span)` | Spawn — returns the process handle |
| `_collect_response(proc, span, start)` | Today's behavior: `proc.communicate()` + JSON envelope parse + `ClaudeResponse` |
| `_iterate_stream(proc, span, start)` | New: `async for line in proc.stdout`, yield events, handle subprocess lifecycle |

Existing synchronous methods continue calling `_spawn_subprocess` → `_collect_response`. New `send_stream()` calls `_spawn_subprocess` → `_iterate_stream`. Identical env, OTEL, session args, timeout.

### 5.5 Cancellation Contract

When the consumer abandons the iterator (`break`, raise, `aclose()`):

1. The async-generator's `finally:` block runs.
2. If subprocess alive: `proc.kill()`, `await proc.wait()`.
3. No event is yielded after cancellation.
4. Parent span closes with `status=CANCELLED`.

Player-interrupt is then a `break` in the narrator's iteration loop. No special API.

### 5.6 Timeout

Existing `self._timeout` applies **end-to-end** (spawn → stream EOS), not per-token. On timeout:

1. Iterator yields `StreamError(kind="timeout", partial_text=accumulated, ...)`.
2. Subprocess killed and reaped.
3. Iterator ends.

The narrator decides what to do with `StreamError` (persist partial as degraded canonical, error frame, retry, etc.).

### 5.7 `StreamFenceParser`

Lives in a new module: `sidequest-server/sidequest/agents/narrator/stream_fence.py` (sibling to `narrator.py`, which is already 729 lines).

```python
class StreamFenceParser:
    """Splits a streaming claude response into prose (live) and game_patch (buffered).

    Driven externally — feed() called per TextDelta, finalize() called at EOS.
    Prose chunks are emitted via the on_prose_delta callback as soon as they
    are confirmed to not be part of a fence. JSON is accumulated internally.
    """

    def __init__(self, on_prose_delta: Callable[[str], Awaitable[None]]):
        ...

    async def feed(self, chunk: str) -> None:
        """Process one TextDelta. May invoke on_prose_delta zero or more times."""

    async def finalize(self) -> FenceParseResult:
        """Call exactly once after stream EOS. Flushes any remaining carry."""

@dataclass(frozen=True, slots=True)
class FenceParseResult:
    prose: str
    game_patch_json: str | None
    status: Literal["complete", "no_fence", "unclosed_fence", "trailing_garbage"]
    fence_offset: int | None
```

#### State Machine

| State | Forwards to `on_prose_delta`? | Buffers? |
|---|---|---|
| `PROSE` | yes (except small lookahead tail) | lookahead tail only |
| `JSON_BUFFERING` | no | yes — to `_json_buffer` |
| `EPILOGUE` | no | discards (logs `trailing_garbage`) |

```
                  detect "\n```game_patch" + (newline | EOS)
PROSE  ─────────────────────────────────────────────────────►  JSON_BUFFERING
                                                                       │
                                                                       │ detect "\n```" + (newline | EOS)
                                                                       ▼
                                                                  EPILOGUE
                                                                  (discard)
```

#### Lookahead Buffer

In `PROSE`, the parser holds back a carry tail of up to `len("\n```game_patch") = 14` bytes. Any chunk-boundary cut through a fence is recoverable on the next chunk.

```python
self._carry += chunk

while True:
    match = OPEN_FENCE.search(self._carry)
    if match:
        prefix = self._carry[:match.start()]
        if prefix:
            await self._on_prose_delta(prefix)
            self._prose_total += prefix
        self._carry = self._carry[match.end():]
        self._state = JSON_BUFFERING
        return await self._feed_json(self._carry)

    safe_emit_len = max(0, len(self._carry) - LOOKAHEAD_BYTES)
    if safe_emit_len > 0:
        emit = self._carry[:safe_emit_len]
        self._carry = self._carry[safe_emit_len:]
        await self._on_prose_delta(emit)
        self._prose_total += emit
    return
```

Same approach in `JSON_BUFFERING` for close-fence detection.

#### Boundary Patterns

```python
OPEN_FENCE = re.compile(r"\r?\n```game_patch[ \t]*\r?\n", re.MULTILINE)
CLOSE_FENCE = re.compile(r"\r?\n```[ \t]*\r?\n", re.MULTILINE)
```

The label requirement (`game_patch`) makes the open boundary unambiguous against any prose-embedded code fence (`` ```python ``, `` ```text ``, bare `` ``` ``).

#### Edge-Case Handling

| Case | Behavior |
|---|---|
| Single/double backticks in prose | Pass through; pattern requires triple-backtick + label |
| Triple-backticks with non-`game_patch` label (`` ```python ``, `` ```yaml ``) | Pass through; label-specific |
| Bare triple-backticks in prose | Pass through; label-specific |
| `` ```game_patch `` glued to prior word (no leading newline) | Not detected. Acceptable risk. Logged as `no_fence`. |
| EOS in `PROSE` | `status=no_fence`, `game_patch_json=None`. Empty patch this turn. |
| EOS in `JSON_BUFFERING` (LLM truncated) | `status=unclosed_fence`. Best-effort `json.loads` on buffer. |
| Pretty-printed JSON | Handled — close-fence requires `\n```` at start-of-line, unambiguous outside JSON syntax |
| `\n```\n` literally inside a JSON string | Cannot occur — JSON syntax forbids unescaped newlines in string literals |
| Multiple `game_patch` blocks (off-script) | Second block discarded as `trailing_garbage`. Logged. |
| Content after close fence | Discarded. `status=trailing_garbage`. Logged. |
| `\r\n` line endings | Handled via `\r?\n` in regex |

### 5.8 Narrator Integration

`narrator.respond()` gains a streaming branch behind the feature flag:

```python
if os.getenv("SIDEQUEST_NARRATOR_STREAMING") == "1":
    return await self._respond_streaming(prompt, ...)
return await self._respond_synchronous(prompt, ...)  # today's path, unchanged
```

The streaming variant:

```python
async def _respond_streaming(self, prompt: str, ..., turn_id: str):
    seq = 0
    async def on_prose_delta(chunk: str) -> None:
        nonlocal seq
        await broadcast_delta(turn_id=turn_id, chunk=chunk, seq=seq, room=room)
        seq += 1

    parser = StreamFenceParser(on_prose_delta=on_prose_delta)
    stream_meta: StreamComplete | StreamError | None = None

    async for event in client.send_stream(prompt, model=..., session_id=...):
        match event:
            case TextDelta(text=t):
                await parser.feed(t)
            case StreamComplete() as done:
                stream_meta = done
            case StreamError() as err:
                stream_meta = err

    result = await parser.finalize()

    if isinstance(stream_meta, StreamError):
        return await self._handle_stream_error(stream_meta, result)

    # Existing path: parse game_patch JSON, emit canonical event
    game_patch = parse_game_patch(result.game_patch_json) if result.game_patch_json else None
    await emit_event(handler, kind="narration", payload=NarrationPayload(
        text=result.prose,
        ... # plus all the existing per-turn metadata
    ))
    if game_patch is not None:
        await emit_event(handler, kind="game_patch", payload=game_patch)

    return result
```

The post-EOS logic from line "parse game_patch" downward is **unchanged** from today's synchronous path — same `emit_event` calls, same `projection_filter` + `perception_rewriter` invocations during fan-out.

### 5.9 WebSocket Protocol — `narration.delta`

```typescript
{
  "kind": "narration.delta",
  "payload": {
    "turn_id": string,        // ties deltas to a specific in-flight turn
    "chunk": string,          // a piece of prose; concatenation in order = full prose so far
    "seq": number             // monotonic per turn_id, starting at 0
  }
}
```

**Per-turn frame ordering on the wire:**

```
narration.delta  seq=0  turn_id=T  chunk="**The Collapsed Overpass**\n\n"
narration.delta  seq=1  turn_id=T  chunk="Rust dust drifts down from the..."
narration.delta  seq=2  turn_id=T  chunk="...rebar above. Felix's lantern"
...
narration.delta  seq=N  turn_id=T  chunk="...as the door grinds shut."
─── stream EOS ──────────────────────────────────────────────────
narration         seq=...  turn_id=T  payload={text: "...full canonical...", ...}   ← event-sourced
game_patch        seq=...  turn_id=T  payload={items_lost: [...], ...}              ← event-sourced
```

Terminal `narration` and `game_patch` frames are **byte-identical to today's**. They carry the existing per-player projection-cache `seq` (Invariant 3 — assigned by `EventLog.append_in_transaction`).

### 5.10 `broadcast_delta()` Helper

In `server/emitters.py`:

```python
async def broadcast_delta(
    *,
    turn_id: str,
    chunk: str,
    seq: int,
    room: Room,
) -> None:
    """Broadcast an ephemeral narration delta to all sockets in the room.

    Does NOT call emit_event(). Does NOT touch the projection cache.
    Does NOT run perception_rewriter. Pure presentation channel.
    """
    msg = NarrationDelta(payload=NarrationDeltaPayload(
        turn_id=turn_id, chunk=chunk, seq=seq,
    ))
    for socket in room.connected_sockets():
        await socket.send_json(msg.model_dump())
```

### 5.11 Backpressure (v1)

**Policy:** buffer-all per-socket. WebSocket frames queued at the asyncio layer. If a client falls behind, the per-socket queue grows; eventually kernel send buffer fills and writes block.

**Per-socket queue depth metric** in OTEL — emit `ws.socket.queue_depth` per socket every N frames. If metrics show queues regularly exceeding M frames, add coalescing in v2.

**Terminal canonical frame is delivered regardless** — even if a client misses every delta, the swap-to-canonical at end-of-turn delivers the full text.

### 5.12 Frontend Render Contract

| Module | Today | Change |
|---|---|---|
| `src/screens/Narration*.tsx` | Renders `narration` payload from state mirror | Subscribes to delta stream; per-turn accumulator; renders accumulated-or-canonical |
| `src/lib/wsClient.ts` | Typed message dispatch | New handler for `narration.delta` |
| `src/types/messages.ts` | `GameMessage` union | New `NarrationDelta` variant |
| `src/providers/GameStateProvider.tsx` | Mirrors authoritative state | Per-turn delta buffer keyed by `turn_id`; cleared 5s after canonical lands |

```typescript
type StreamingNarrationState = {
  turns: Map<string, {
    chunks: string[];
    nextExpectedSeq: number;
    canonical: string | null;
  }>;
};

// Render rule per turn:
const display_text = canonical ?? chunks.join('');
```

#### Frontend Failure Handling

| Event | Behavior |
|---|---|
| `narration.delta` arrives with unexpected seq (gap) | Render whatever is accumulated; canonical event will land and swap |
| `narration.delta` arrives for a `turn_id` whose canonical landed | Discard. Late delta. Console log. |
| Canonical `narration` arrives without preceding deltas (sync turn or reconnect) | Render canonical directly. No special path. |
| Stream stalls (>5s no delta, no canonical) | Show "narrator considers" interstitial |

## 6. OTEL Instrumentation

### Spans

| Span | When | Key Attributes |
|---|---|---|
| `narrator.stream.start` | Spawn | `turn_id`, `prompt_tokens`, `model`, `session_id` |
| `narrator.stream.first_token` | First `TextDelta` | `ttft_seconds`, `turn_id` |
| `narrator.stream.fence_detected` | Parser → `JSON_BUFFERING` | `turn_id`, `prose_bytes_at_fence`, `seconds_to_fence` |
| `narrator.stream.delta` | Each prose delta (sampled 1/8) | `turn_id`, `seq`, `chunk_bytes` |
| `narrator.stream.complete` | Terminal success | `turn_id`, `total_seconds`, `ttft_seconds`, `prose_bytes`, `delta_count`, `json_parse_status`, `input_tokens`, `output_tokens` |
| `narrator.stream.error` | Terminal failure | `turn_id`, `error_kind`, `partial_prose_bytes`, `total_seconds`, `detail` |
| `narrator.stream.cancelled` | Iterator closed before EOS | `turn_id`, `reason`, `partial_prose_bytes` |

The existing `agent_call_session_span` (the parent that wraps the whole narrator turn) gains `ttft_seconds` and `terminal_kind` attributes so it remains the single roll-up signal for "how long did this turn take."

### Sampling

A 60s turn at typical generation rates produces 200–400 deltas. Per-delta spans are too chatty. **Sample 1/8** (configurable), always emit seq 0 (first delta) and the last delta. Aggregate counters live on `narrator.stream.complete`.

### GM Panel Visualizations

Three new panels in the dashboard at `sidequest-server /dashboard`:

| Visualization | Source | Tells us |
|---|---|---|
| TTFT distribution histogram | `narrator.stream.first_token.ttft_seconds` | Spawn-to-first-token health. Regressions show here. |
| Stream timeline (per-turn waterfall) | start → first_token → fence_detected → complete | Where the 60s went: cold start, prose, JSON tail, dispatch overhead |
| JSON parse status pie | `narrator.stream.complete.json_parse_status` | LLM behavior signal. `complete` should dominate. |

### The Lie-Detector Test

After streaming ships, this test must pass for every narrated turn:

> Pick any turn. The Stream Timeline must show `first_token` happening 1–3s after `start`. The dashboard's per-turn waterfall must show `narrator.stream.complete.delta_count > 0`. If either is absent or stuck on the same value across turns, the streaming pipeline is silently regressed.

## 7. Failure Modes

| Failure | Player visible | Server | OTEL signal |
|---|---|---|---|
| Subprocess fails to spawn | Spinner, then error dialog (existing path) | `StreamError(subprocess_failed)`, no canonical event | `narrator.stream.error.error_kind=subprocess_failed` |
| Stream timeout | Whatever prose arrived stays; no patch applied | Persist partial as best-effort canonical; warn | `narrator.stream.error.error_kind=timeout`, `partial_prose_bytes>0` |
| EOS, no fence | Full prose displayed; no state mutation | Empty patch; warn | `narrator.stream.complete.json_parse_status=no_fence` |
| EOS, unclosed fence | Full prose displayed; patch applied if buffer parses, else not | Best-effort `json.loads`; warn either way | `narrator.stream.complete.json_parse_status=unclosed_fence` |
| Trailing content after close fence | Prose + patch fine; trailer discarded | Warn | `narrator.stream.complete.json_parse_status=trailing_garbage` |
| Player interrupt mid-stream | Partial prose disappears (next turn replaces) | `aclose()` → kill subprocess → no canonical | `narrator.stream.cancelled.reason=player_interrupt` |
| WS disconnect mid-stream | Reconnect renders only canonical | Server keeps streaming to remaining sockets | (existing socket lifecycle) |
| MP: one player's WS slow | Each socket independent; no slowdown for others | Per-socket queue grows | `ws.socket.queue_depth` |

## 8. Test Strategy

### Unit Tests — `claude_client.send_stream`

Spawn function is dependency-injected; tests substitute a canned-NDJSON fake.

| Test | Coverage |
|---|---|
| `stream_yields_deltas_in_order` | Canned input with N text events → N `TextDelta`s, then `StreamComplete` |
| `stream_yields_complete_with_usage` | Final result event populates token counts and session_id |
| `stream_yields_error_on_subprocess_fail` | Non-zero exit → `StreamError(kind=subprocess_failed)` |
| `stream_yields_error_on_timeout` | Slow fake stream + short timeout → `StreamError(kind=timeout, partial_text=...)` |
| `stream_yields_error_on_empty` | Empty stdout → `StreamError(kind=empty)` |
| `stream_ignores_unknown_event_kinds` | Forward-compat — unknown event kind doesn't break the stream |
| `stream_handles_malformed_lines` | One bad line in the middle → logged warning, stream continues |
| `cancel_kills_subprocess` | Iterator `aclose()` → process killed |
| `terminal_event_invariant` | Every test asserts exactly one `StreamComplete` or `StreamError` |

### Unit Tests — `StreamFenceParser`

| Test | Coverage |
|---|---|
| `prose_only_no_fence` | Pure prose stream → all flushed as prose, `status=no_fence` |
| `clean_split` | Prose + open + JSON + close → `status=complete`, prose preserved exactly, JSON preserved exactly |
| `chunk_at_every_boundary` | Parameterized: split known input at every byte boundary → identical `FenceParseResult` |
| `fence_in_prose_passthrough` | Prose containing `` ```python `` and bare triple-backticks → pass through |
| `unclosed_fence` | Open fence with no close → `status=unclosed_fence`, JSON buffer = everything after open |
| `truncated_at_open_fence` | Stream ends mid-fence-label (`\n``game_pa`) → must NOT emit partial-fence as prose; treat as `no_fence` after finalize flush |
| `pretty_printed_json` | Multi-line indented JSON → round-trips exactly |
| `crlf_line_endings` | `\r\n` variant → same behavior |
| `trailing_garbage_logged` | Content after close → `status=trailing_garbage`, JSON preserved |
| `prose_delta_callback_order` | `on_prose_delta` calls in stream order, never out-of-order, concatenate to `result.prose` |

### Integration Tests

| Test | Coverage |
|---|---|
| `narrator_streaming_path_e2e_mock` | Mock `claude_client.send_stream` with canned NDJSON; assert WS broadcast saw N delta frames + 1 canonical narration + 1 game_patch in order |
| `narrator_streaming_disabled_by_flag` | Flag off → existing synchronous path used, deltas not broadcast |
| `multiplayer_deltas_to_all_sockets` | Two connected players → both receive every delta; canonical event is per-player filtered as today |
| `streaming_subprocess_crash_recovery` | Mock crashes mid-stream → partial deltas already broadcast, narration screen shows partial prose, no game_patch event |
| `lie_detector_otel_spans_present` | Successful turn → assert `narrator.stream.start`, `.first_token`, `.complete` spans present with non-empty attributes |

### Wiring Test (per CLAUDE.md)

> Every test suite needs a wiring test that verifies the component is imported, called, and reachable from production code paths.

| Test | Coverage |
|---|---|
| `streaming_flag_on_narrator_uses_send_stream` | With `SIDEQUEST_NARRATOR_STREAMING=1`, exercising a real narrator turn calls `claude_client.send_stream` (verified by spy / mock); without the flag, calls `send_with_session` |

### Frontend Tests

| Test | Coverage |
|---|---|
| `delta_accumulator_appends_in_seq_order` | Mock WS message delivery → state mirror builds `chunks: string[]` correctly |
| `canonical_swap_replaces_accumulated` | After deltas, on `narration` event → display becomes canonical, not concatenated chunks |
| `late_delta_after_canonical_discarded` | Delta arriving after canonical → ignored, console-logged |
| `stalled_stream_shows_interstitial` | No delta + no canonical for >5s → "narrator considers" indicator |

## 9. Sequencing & Scope

### Three Stories, One Epic, Feature-Flagged Throughout

| Story | Points | Repos | Behind flag? | Ships |
|---|---|---|---|---|
| Streaming client + parser | 5 | server | yes | `claude_client.send_stream()`, `StreamFenceParser` + full unit-test coverage; narrator gains streaming path but defaults to synchronous unless flag set |
| WS protocol + emitter + OTEL | 3 | server | yes | `narration.delta` message, `broadcast_delta()` helper, OTEL spans, GM panel histograms. Server emits deltas when flag on. |
| Frontend incremental render | 3 | ui | yes | UI subscribes to deltas, accumulates, swaps to canonical at EOS. Behind same flag. |

**Total: 11 points, 1 epic.**

**Flag-flip ordering:** all three land server-ready and frontend-ready, then flip `SIDEQUEST_NARRATOR_STREAMING=1` for the playgroup's next session. If lie-detector dashboard shows healthy TTFT and complete-rate, flag becomes default. If not, flip back — no player-visible regression.

### Sprint Placement

Sprint 3 closes 2026-05-10 with 19 points already in flight; this work fits naturally as the first epic of Sprint 4. If a faster derisk is wanted before Sprint 4, the **streaming client + parser** story alone (server-side only, behind flag, no UI) can ship in Sprint 3 tail to validate the Claude CLI streaming contract — this gives concrete OTEL TTFT numbers without committing to the WS / UI half.

## 10. Open Questions for Implementation Phase

1. **Exact NDJSON event field paths** — verify against current Claude CLI output. Prepare a captured `stream-json` sample as a test fixture before writing the consumer.
2. **`turn_id` source** — does the existing `GameMessage` envelope carry a turn ID? If not, mint one in the narrator at the top of each turn and thread through. (Not load-bearing; either path works.)
3. **First-token interstitial duration** — when do we show "narrator considers"? Recommendation: only for the first 1.5s after submission, fade out as soon as the first delta lands. UX-Designer can iterate.
4. **OTEL attribute cardinality** — `turn_id` as a span attribute is cardinality-unbounded. Confirm OTEL exporter handles this (it does for traces; may need verification for metrics).

## 11. References

- ADR-038 — WebSocket Transport Architecture
- ADR-066 — Persistent Opus Narrator Sessions
- ADR-067 — Unified Narrator Agent (single persistent session)
- ADR-026 — Client-Side State Mirror
- ADR-090 — OTEL Dashboard Restoration after Python Port
- `sidequest-server/sidequest/agents/claude_client.py` — current synchronous client
- `sidequest-server/sidequest/agents/narrator.py:80-93` — PART 1 / PART 2 prompt contract
- `sidequest-server/sidequest/agents/perception_rewriter.py` — current per-recipient filter (no-op for narration today)
- `sidequest-server/sidequest/server/emitters.py` — existing `emit_event()` pipeline (unchanged by this design)
- `CLAUDE.md` — OTEL Observability Principle, "Every Test Suite Needs a Wiring Test"
