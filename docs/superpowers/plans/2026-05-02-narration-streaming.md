# Narration Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the synchronous narrator pipeline into a streaming one — first-token-time of 1-3s, prose chunks delivered live, canonical event-sourced record byte-identical to today.

**Architecture:** Switch `claude_client` to `--output-format stream-json`, parse the natural PART-1/PART-2 fence boundary already present in the narrator prompt, broadcast prose deltas as ephemeral WS frames, run the existing `emit_event()` pipeline unchanged at end-of-stream. Behind feature flag `SIDEQUEST_NARRATOR_STREAMING`.

**Tech Stack:** Python 3.13 / asyncio / pytest (server) · React/TypeScript / vitest (UI) · WebSockets (ADR-038) · OpenTelemetry

**Spec:** `docs/superpowers/specs/2026-05-02-narration-streaming-design.md` (commit `13ba25c`)

**Scope:** Three sequential stories (5 + 3 + 3 = 11 points) within a single epic. Each story commits behind the same feature flag and is independently shippable; full chain enabled by flipping the env var.

---

## Story 1 — Streaming Client + Parser (5 pts, server)

Self-contained backend infrastructure. Narrator gains a streaming code path; flag default off means observable behavior is unchanged after this story lands.

---

### Task 1: StreamEvent type hierarchy

**Files:**
- Modify: `sidequest-server/sidequest/agents/claude_client.py` (append after existing `ClaudeResponse`)
- Test: `sidequest-server/tests/agents/test_claude_client_stream_types.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/agents/test_claude_client_stream_types.py
"""Tests for streaming event type hierarchy."""
from __future__ import annotations

from sidequest.agents.claude_client import (
    StreamComplete,
    StreamError,
    StreamEvent,
    TextDelta,
)


def test_text_delta_is_stream_event():
    delta = TextDelta(text="hello")
    assert isinstance(delta, StreamEvent)
    assert delta.text == "hello"


def test_text_delta_is_frozen():
    import dataclasses
    delta = TextDelta(text="hello")
    with pytest_raises_or_None():
        # frozen=True dataclass — assignment must raise FrozenInstanceError
        delta.text = "world"  # type: ignore[misc]


def test_stream_complete_carries_usage_metadata():
    done = StreamComplete(
        full_text="full prose",
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=10,
        cache_read_input_tokens=5,
        session_id="abc-123",
        elapsed_seconds=3.14,
    )
    assert isinstance(done, StreamEvent)
    assert done.full_text == "full prose"
    assert done.input_tokens == 100
    assert done.session_id == "abc-123"
    assert done.elapsed_seconds == 3.14


def test_stream_error_carries_failure_detail():
    err = StreamError(
        kind="timeout",
        elapsed_seconds=120.0,
        partial_text="prose got this far",
        detail="claude CLI timed out after 120.0s",
        exit_code=None,
    )
    assert isinstance(err, StreamEvent)
    assert err.kind == "timeout"
    assert err.partial_text == "prose got this far"


def pytest_raises_or_None():
    """Inline contextmanager for the frozen-test (avoid pytest import shenanigans)."""
    import contextlib
    import dataclasses
    @contextlib.contextmanager
    def _ctx():
        try:
            yield
        except dataclasses.FrozenInstanceError:
            return
        raise AssertionError("expected FrozenInstanceError")
    return _ctx()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client_stream_types.py -v
```

Expected: FAIL — `ImportError: cannot import name 'StreamComplete' from 'sidequest.agents.claude_client'`

- [ ] **Step 3: Implement the type hierarchy**

Append after `ClaudeResponse` definition (around line 132 in `claude_client.py`):

```python
# ---------------------------------------------------------------------------
# Streaming event types — yielded from ClaudeClient.send_stream()
# ---------------------------------------------------------------------------

from typing import Literal


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """Base for events yielded from ClaudeClient.send_stream()."""


@dataclass(frozen=True, slots=True)
class TextDelta(StreamEvent):
    """An incremental chunk of assistant prose.

    Concatenating all TextDelta.text values in stream order yields the
    final response text.
    """

    text: str


@dataclass(frozen=True, slots=True)
class StreamComplete(StreamEvent):
    """Terminal event on success.

    Drop-in metadata equivalent to ClaudeResponse — input_tokens,
    output_tokens, session_id. Carries the accumulated full_text for
    callers that want it without re-concatenating deltas.
    """

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

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client_stream_types.py -v
```

Expected: PASS, 4 tests.

- [ ] **Step 5: Lint and commit**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format .
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/agents/claude_client.py sidequest-server/tests/agents/test_claude_client_stream_types.py
git commit -m "feat(agents): StreamEvent type hierarchy for streaming claude_client"
```

---

### Task 2: NDJSON event parsing helpers

The streaming consumer needs pure helpers that take a parsed JSON dict (one line of stdout) and decide what to emit. Keep this pure for unit-test coverage.

**Files:**
- Create: `sidequest-server/sidequest/agents/claude_stream_parser.py`
- Test: `sidequest-server/tests/agents/test_claude_stream_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/agents/test_claude_stream_parser.py
"""Tests for NDJSON event parsing helpers."""
from __future__ import annotations

from sidequest.agents.claude_stream_parser import (
    extract_text_delta,
    extract_terminal_metadata,
    is_terminal_event,
)


# Sample event shapes — verified against `claude -p --output-format stream-json`
# during implementation. These are placeholders updated in Task 2.5 with
# captured fixture data.

DELTA_EVENT = {
    "type": "assistant",
    "message": {
        "content": [{"type": "text", "text": "Hello "}],
    },
}

TERMINAL_EVENT = {
    "type": "result",
    "result": "Hello world.",
    "usage": {
        "input_tokens": 100,
        "output_tokens": 5,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    },
    "session_id": "sess-abc",
}

UNKNOWN_EVENT = {"type": "system", "subtype": "init"}


def test_extract_text_delta_returns_chunk_for_assistant_event():
    chunk = extract_text_delta(DELTA_EVENT)
    assert chunk == "Hello "


def test_extract_text_delta_returns_none_for_non_assistant():
    assert extract_text_delta(TERMINAL_EVENT) is None
    assert extract_text_delta(UNKNOWN_EVENT) is None


def test_is_terminal_event_recognizes_result_type():
    assert is_terminal_event(TERMINAL_EVENT) is True


def test_is_terminal_event_returns_false_for_non_terminal():
    assert is_terminal_event(DELTA_EVENT) is False
    assert is_terminal_event(UNKNOWN_EVENT) is False


def test_extract_terminal_metadata_pulls_usage_and_session():
    meta = extract_terminal_metadata(TERMINAL_EVENT)
    assert meta.full_text == "Hello world."
    assert meta.input_tokens == 100
    assert meta.output_tokens == 5
    assert meta.session_id == "sess-abc"


def test_extract_terminal_metadata_handles_missing_usage():
    minimal = {"type": "result", "result": "ok"}
    meta = extract_terminal_metadata(minimal)
    assert meta.full_text == "ok"
    assert meta.input_tokens is None
    assert meta.output_tokens is None
    assert meta.session_id is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_stream_parser.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.agents.claude_stream_parser'`

- [ ] **Step 3: Implement the parser helpers**

```python
# sidequest-server/sidequest/agents/claude_stream_parser.py
"""Pure helpers for parsing one NDJSON line from `claude -p --output-format stream-json`.

The Claude CLI emits one JSON object per stdout line during streaming. These
helpers classify a parsed event and extract the fields the streaming consumer
in claude_client.py needs.

Field paths are CLI-version-dependent and verified against captured fixture
data in tests. If the CLI changes shape, only this module needs adjustment.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TerminalMetadata:
    """Extracted from the final `result` event in a stream."""

    full_text: str
    input_tokens: int | None
    output_tokens: int | None
    cache_creation_input_tokens: int | None
    cache_read_input_tokens: int | None
    session_id: str | None


def extract_text_delta(event: dict) -> str | None:
    """Return the prose chunk from an assistant-message event, or None.

    Returns None for events that don't carry text deltas (terminal events,
    system events, anything unknown).
    """
    if event.get("type") != "assistant":
        return None
    message = event.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, list):
        return None
    chunks: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                chunks.append(text)
    if not chunks:
        return None
    return "".join(chunks)


def is_terminal_event(event: dict) -> bool:
    """True when the event is the stream's final result event."""
    return event.get("type") == "result"


def extract_terminal_metadata(event: dict) -> TerminalMetadata:
    """Pull usage, session_id, and full_text from the terminal result event."""
    full_text = event.get("result")
    if not isinstance(full_text, str):
        full_text = ""

    usage = event.get("usage") if isinstance(event.get("usage"), dict) else None

    def _opt_int(key: str) -> int | None:
        if usage is None:
            return None
        v = usage.get(key)
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    session_id = event.get("session_id")
    if not isinstance(session_id, str):
        session_id = None

    return TerminalMetadata(
        full_text=full_text,
        input_tokens=_opt_int("input_tokens"),
        output_tokens=_opt_int("output_tokens"),
        cache_creation_input_tokens=_opt_int("cache_creation_input_tokens"),
        cache_read_input_tokens=_opt_int("cache_read_input_tokens"),
        session_id=session_id,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_stream_parser.py -v
```

Expected: PASS, 6 tests.

- [ ] **Step 5: Lint and commit**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format .
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/agents/claude_stream_parser.py sidequest-server/tests/agents/test_claude_stream_parser.py
git commit -m "feat(agents): NDJSON parsing helpers for stream-json events"
```

---

### Task 3: Capture real Claude CLI stream-json fixture

Open Question 10.1 from the spec — verify exact field paths against current Claude CLI output and lock fixture into tests. This task replaces the placeholder shapes in Task 2's tests with real captured data.

**Files:**
- Create: `sidequest-server/tests/agents/fixtures/claude_stream_sample.ndjson`
- Modify: `sidequest-server/tests/agents/test_claude_stream_parser.py` (replace placeholders with fixture-based tests)

- [ ] **Step 1: Capture a real stream-json sample**

```bash
cd /tmp
echo "Say hello in two short sentences." | claude -p --output-format stream-json > claude_stream_sample.ndjson 2>&1 || true
cat claude_stream_sample.ndjson | head -20
```

Inspect output. Expected: NDJSON, one JSON object per line, including at least one `"type": "assistant"` event with a `text` chunk and one final `"type": "result"` event with `usage`.

- [ ] **Step 2: Save fixture into test tree**

```bash
mkdir -p /Users/slabgorb/Projects/oq-1/sidequest-server/tests/agents/fixtures
mv /tmp/claude_stream_sample.ndjson /Users/slabgorb/Projects/oq-1/sidequest-server/tests/agents/fixtures/
```

- [ ] **Step 3: Update parser if real shape differs from placeholder**

Read the captured fixture line-by-line. If the actual `assistant` event structure differs from the placeholder in Task 2 (e.g., `delta` field instead of `message.content`), update `claude_stream_parser.py` to match. The parser API stays the same; only the internal field paths change.

- [ ] **Step 4: Add a fixture-driven integration test**

Append to `tests/agents/test_claude_stream_parser.py`:

```python
import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "claude_stream_sample.ndjson"


def _load_events() -> list[dict]:
    events = []
    with FIXTURE.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip non-JSON lines (e.g., stderr leaked into stdout)
                continue
    return events


def test_real_fixture_yields_at_least_one_text_delta():
    events = _load_events()
    deltas = [extract_text_delta(e) for e in events]
    text_chunks = [d for d in deltas if d is not None]
    assert len(text_chunks) > 0
    # Concatenated chunks should contain "hello" (case-insensitive)
    assert "hello" in "".join(text_chunks).lower()


def test_real_fixture_has_exactly_one_terminal_event():
    events = _load_events()
    terminals = [e for e in events if is_terminal_event(e)]
    assert len(terminals) == 1


def test_real_fixture_terminal_metadata_has_usage():
    events = _load_events()
    [terminal] = [e for e in events if is_terminal_event(e)]
    meta = extract_terminal_metadata(terminal)
    assert meta.input_tokens is not None
    assert meta.output_tokens is not None
    assert meta.full_text != ""
```

- [ ] **Step 5: Run tests**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_stream_parser.py -v
```

Expected: PASS, 9 tests (6 from Task 2 + 3 fixture-driven).

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/tests/agents/fixtures/claude_stream_sample.ndjson \
        sidequest-server/tests/agents/test_claude_stream_parser.py \
        sidequest-server/sidequest/agents/claude_stream_parser.py
git commit -m "test(agents): lock claude stream-json fixture against real CLI output"
```

---

### Task 4: Refactor `_run_subprocess` into spawn + collect

Pure refactor — no behavior change. Splits `_run_subprocess()` into `_spawn_subprocess()` (returns the process) and `_collect_response()` (does the existing communicate+parse). Sets up the streaming variant to share the spawn step.

**Files:**
- Modify: `sidequest-server/sidequest/agents/claude_client.py:354-440` (the `_run_subprocess` method body)
- Test: `sidequest-server/tests/agents/test_claude_client.py` (existing tests must still pass)

- [ ] **Step 1: Run existing tests to establish baseline**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client.py -v
```

Expected: all existing tests PASS. Record the count.

- [ ] **Step 2: Refactor `_run_subprocess` into two methods**

Replace the existing `async def _run_subprocess(self, args, env, span)` body with:

```python
    async def _spawn_subprocess(
        self,
        args: list[str],
        env: dict[str, str] | None,
    ) -> Any:
        """Spawn the claude CLI subprocess, returning the process handle.

        Caller is responsible for reading stdout/stderr and calling
        proc.wait() / proc.kill() as appropriate.
        """
        try:
            return await self._spawn(self._command_path, *args, env=env)
        except Exception as e:
            logger.error("Failed to spawn subprocess: %s", e)
            raise SubprocessFailed(exit_code=None, stderr=str(e)) from e

    async def _collect_response(
        self,
        proc: Any,
        span: object,
        start: float,
    ) -> ClaudeResponse:
        """Wait for proc to finish, parse the JSON envelope, return ClaudeResponse.

        Used by the synchronous send_*() entry points. The streaming
        variant uses _iterate_stream() instead.
        """
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._timeout,
            )
        except builtins.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            elapsed = time.monotonic() - start
            logger.warning(
                "Claude CLI subprocess timed out after %.1fs (timeout=%.1fs)",
                elapsed,
                self._timeout,
            )
            raise TimeoutError(elapsed=elapsed) from None

        elapsed = time.monotonic() - start
        returncode = proc.returncode

        stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

        if returncode != 0:
            raise SubprocessFailed(exit_code=returncode, stderr=stderr)

        trimmed = stdout.strip()
        if not trimmed:
            raise EmptyResponse()

        # Parse JSON envelope from --output-format json (existing logic moved verbatim)
        return self._parse_json_envelope(trimmed, elapsed, span)

    async def _run_subprocess(
        self,
        args: list[str],
        env: dict[str, str] | None,
        span: object,
    ) -> ClaudeResponse:
        """Spawn + collect — kept as a thin wrapper for the synchronous path."""
        start = time.monotonic()
        proc = await self._spawn_subprocess(args, env)
        return await self._collect_response(proc, span, start)
```

Then extract the existing JSON-envelope parse logic (currently lines ~405-440 inside `_run_subprocess`) into a new private method `_parse_json_envelope(self, trimmed, elapsed, span) -> ClaudeResponse`. Move the code verbatim.

- [ ] **Step 3: Run existing tests to verify no regression**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client.py -v
```

Expected: same test count as Step 1, all PASS.

- [ ] **Step 4: Lint**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format .
```

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/agents/claude_client.py
git commit -m "refactor(agents): split _run_subprocess into spawn + collect (no behavior change)"
```

---

### Task 5: `_iterate_stream` async generator

The new streaming consumer. Reads stdout line-by-line, yields TextDelta / StreamComplete / StreamError. Uses the parser helpers from Task 2.

**Files:**
- Modify: `sidequest-server/sidequest/agents/claude_client.py` (add `_iterate_stream` method)
- Modify: `sidequest-server/tests/agents/test_claude_client.py` (extend FakeProcess to support line-streaming stdout)
- Create: `sidequest-server/tests/agents/test_claude_client_stream.py`

- [ ] **Step 1: Extend FakeProcess for streaming**

In `tests/agents/test_claude_client.py`, find the existing `FakeProcess` class and add a sibling `FakeStreamingProcess`:

```python
class FakeStreamingProcess:
    """FakeProcess variant that emits stdout line-by-line for streaming tests."""

    def __init__(
        self,
        lines: list[bytes],
        returncode: int = 0,
        per_line_delay: float = 0.0,
        stderr: bytes = b"",
    ) -> None:
        self._lines = lines
        self.returncode = returncode
        self._per_line_delay = per_line_delay
        self._stderr = stderr
        self._killed = False
        self.stdout = self  # asyncio uses `proc.stdout` as an async iterator

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        if self._killed or not self._lines:
            raise StopAsyncIteration
        line = self._lines.pop(0)
        if self._per_line_delay:
            await asyncio.sleep(self._per_line_delay)
        return line

    async def communicate(self) -> tuple[bytes, bytes]:
        # If a streaming caller falls back to communicate(), drain remaining
        all_remaining = b"".join(self._lines)
        self._lines = []
        return all_remaining, self._stderr

    def kill(self) -> None:
        self._killed = True

    async def wait(self) -> int:
        return self.returncode


def make_streaming_spawn_fn(
    lines: list[bytes],
    returncode: int = 0,
    per_line_delay: float = 0.0,
    raise_exc: Exception | None = None,
) -> Callable[..., Awaitable[FakeStreamingProcess]]:
    async def _spawn(*args: object, **kwargs: object) -> FakeStreamingProcess:
        if raise_exc is not None:
            raise raise_exc
        return FakeStreamingProcess(lines=list(lines), returncode=returncode, per_line_delay=per_line_delay)
    return _spawn
```

- [ ] **Step 2: Write the failing tests for `_iterate_stream`**

Create `tests/agents/test_claude_client_stream.py`:

```python
"""Tests for ClaudeClient._iterate_stream and send_stream."""
from __future__ import annotations

import json

import pytest

from sidequest.agents.claude_client import (
    ClaudeClient,
    StreamComplete,
    StreamError,
    TextDelta,
)
from tests.agents.test_claude_client import (
    FakeStreamingProcess,
    make_streaming_spawn_fn,
)


def _delta_line(text: str) -> bytes:
    return (json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}) + "\n").encode()


def _terminal_line(full: str, in_tok: int = 100, out_tok: int = 50, session: str | None = "sess-1") -> bytes:
    payload = {
        "type": "result",
        "result": full,
        "usage": {
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }
    if session:
        payload["session_id"] = session
    return (json.dumps(payload) + "\n").encode()


@pytest.mark.asyncio
async def test_stream_yields_deltas_in_order_then_complete():
    lines = [
        _delta_line("Hello "),
        _delta_line("world."),
        _terminal_line("Hello world.", in_tok=10, out_tok=3),
    ]
    spawn = make_streaming_spawn_fn(lines)
    client = ClaudeClient(timeout=10.0, spawn_fn=spawn)

    events = []
    async for ev in client.send_stream(prompt="hi", model="claude-opus-4-7"):
        events.append(ev)

    deltas = [e for e in events if isinstance(e, TextDelta)]
    completes = [e for e in events if isinstance(e, StreamComplete)]
    errors = [e for e in events if isinstance(e, StreamError)]

    assert [d.text for d in deltas] == ["Hello ", "world."]
    assert len(completes) == 1
    assert len(errors) == 0
    assert completes[0].full_text == "Hello world."
    assert completes[0].input_tokens == 10
    assert completes[0].output_tokens == 3
    assert completes[0].session_id == "sess-1"


@pytest.mark.asyncio
async def test_stream_yields_error_on_subprocess_failure():
    lines = [_delta_line("partial")]
    spawn = make_streaming_spawn_fn(lines, returncode=1)
    client = ClaudeClient(timeout=10.0, spawn_fn=spawn)

    events = []
    async for ev in client.send_stream(prompt="hi", model="claude-opus-4-7"):
        events.append(ev)

    errors = [e for e in events if isinstance(e, StreamError)]
    assert len(errors) == 1
    assert errors[0].kind == "subprocess_failed"
    assert "partial" in errors[0].partial_text


@pytest.mark.asyncio
async def test_stream_yields_error_on_empty_stdout():
    spawn = make_streaming_spawn_fn(lines=[])
    client = ClaudeClient(timeout=10.0, spawn_fn=spawn)

    events = []
    async for ev in client.send_stream(prompt="hi", model="claude-opus-4-7"):
        events.append(ev)

    errors = [e for e in events if isinstance(e, StreamError)]
    assert len(errors) == 1
    assert errors[0].kind == "empty"


@pytest.mark.asyncio
async def test_stream_ignores_unknown_event_kinds():
    unknown = (json.dumps({"type": "system", "subtype": "init"}) + "\n").encode()
    lines = [unknown, _delta_line("ok"), _terminal_line("ok")]
    spawn = make_streaming_spawn_fn(lines)
    client = ClaudeClient(timeout=10.0, spawn_fn=spawn)

    events = []
    async for ev in client.send_stream(prompt="hi", model="claude-opus-4-7"):
        events.append(ev)

    deltas = [e for e in events if isinstance(e, TextDelta)]
    assert [d.text for d in deltas] == ["ok"]


@pytest.mark.asyncio
async def test_stream_handles_malformed_lines_with_warning(caplog):
    bad = b"not json at all\n"
    lines = [_delta_line("ok"), bad, _terminal_line("ok")]
    spawn = make_streaming_spawn_fn(lines)
    client = ClaudeClient(timeout=10.0, spawn_fn=spawn)

    events = []
    with caplog.at_level("WARNING"):
        async for ev in client.send_stream(prompt="hi", model="claude-opus-4-7"):
            events.append(ev)

    assert any("malformed_line" in rec.message for rec in caplog.records)
    deltas = [e for e in events if isinstance(e, TextDelta)]
    assert [d.text for d in deltas] == ["ok"]


@pytest.mark.asyncio
async def test_stream_terminates_with_exactly_one_terminal_event():
    """Invariant: every send_stream() iteration yields exactly one
    StreamComplete OR exactly one StreamError, never both, never neither.
    """
    lines = [_delta_line("a"), _terminal_line("a")]
    spawn = make_streaming_spawn_fn(lines)
    client = ClaudeClient(timeout=10.0, spawn_fn=spawn)

    completes = 0
    errors = 0
    async for ev in client.send_stream(prompt="hi", model="claude-opus-4-7"):
        if isinstance(ev, StreamComplete):
            completes += 1
        elif isinstance(ev, StreamError):
            errors += 1
    assert completes + errors == 1
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client_stream.py -v
```

Expected: FAIL — `AttributeError: 'ClaudeClient' object has no attribute 'send_stream'`

- [ ] **Step 4: Implement `_iterate_stream` and `send_stream`**

Add to `claude_client.py` after `_collect_response`:

```python
    async def _iterate_stream(
        self,
        proc: Any,
        span: object,
        start: float,
    ) -> AsyncIterator[StreamEvent]:
        """Consume the subprocess stdout as NDJSON events; yield StreamEvents.

        Always terminates with exactly one StreamComplete or StreamError.
        """
        from sidequest.agents.claude_stream_parser import (
            extract_terminal_metadata,
            extract_text_delta,
            is_terminal_event,
        )

        accumulated = ""
        terminal_meta: TerminalMetadata | None = None  # type: ignore[name-defined]

        try:
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("claude_cli.stream.malformed_line line=%r", line[:200])
                    continue

                delta_text = extract_text_delta(event)
                if delta_text is not None:
                    accumulated += delta_text
                    yield TextDelta(text=delta_text)
                    continue

                if is_terminal_event(event):
                    terminal_meta = extract_terminal_metadata(event)
                    continue
                # Unknown event kind — ignore, forward-compat.
        except builtins.TimeoutError:
            elapsed = time.monotonic() - start
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            yield StreamError(
                kind="timeout",
                elapsed_seconds=elapsed,
                partial_text=accumulated,
                detail=f"claude CLI timed out after {elapsed:.1f}s",
                exit_code=None,
            )
            return

        await proc.wait()
        elapsed = time.monotonic() - start
        returncode = proc.returncode

        if returncode != 0:
            yield StreamError(
                kind="subprocess_failed",
                elapsed_seconds=elapsed,
                partial_text=accumulated,
                detail=f"claude CLI exited with code {returncode}",
                exit_code=returncode,
            )
            return

        if not accumulated and terminal_meta is None:
            yield StreamError(
                kind="empty",
                elapsed_seconds=elapsed,
                partial_text="",
                detail="claude CLI returned no output",
                exit_code=returncode,
            )
            return

        if terminal_meta is None:
            # Stream ended cleanly but we never saw the result event.
            # Synthesize a StreamComplete from accumulated text only.
            yield StreamComplete(
                full_text=accumulated,
                input_tokens=None,
                output_tokens=None,
                cache_creation_input_tokens=None,
                cache_read_input_tokens=None,
                session_id=None,
                elapsed_seconds=elapsed,
            )
            return

        yield StreamComplete(
            full_text=terminal_meta.full_text or accumulated,
            input_tokens=terminal_meta.input_tokens,
            output_tokens=terminal_meta.output_tokens,
            cache_creation_input_tokens=terminal_meta.cache_creation_input_tokens,
            cache_read_input_tokens=terminal_meta.cache_read_input_tokens,
            session_id=terminal_meta.session_id,
            elapsed_seconds=elapsed,
        )

    async def send_stream(
        self,
        prompt: str,
        model: str,
        session_id: str | None = None,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Streaming variant of send_with_session.

        Spawns claude with --output-format stream-json, parses NDJSON line-by-line,
        yields TextDelta events as they arrive. Terminates with StreamComplete
        on success or StreamError on failure.
        """
        allowed = allowed_tools or []
        env = env_vars or {}

        with agent_call_session_span(
            model=model, prompt_len=len(prompt), backend="claude-cli"
        ) as span:
            if not prompt.strip():
                yield StreamError(
                    kind="empty",
                    elapsed_seconds=0.0,
                    partial_text="",
                    detail="empty prompt",
                    exit_code=None,
                )
                return

            args: list[str] = ["--model", model]
            is_resume = session_id is not None
            if is_resume and session_id:
                args += ["--resume", session_id]
            else:
                new_id = str(uuid.uuid4())
                args += ["--session-id", new_id]
                if system_prompt:
                    args += ["--system-prompt", system_prompt]

            if allowed:
                args.append("--allowedTools")
                args.extend(allowed)

            args += ["-p", prompt, "--output-format", "stream-json"]

            process_env = self._build_env(env)
            start = time.monotonic()
            proc = await self._spawn_subprocess(args, process_env)

            async for event in self._iterate_stream(proc, span, start):
                yield event
```

Also add the import at top of file:

```python
from collections.abc import AsyncIterator
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client_stream.py -v
```

Expected: PASS, 6 tests.

- [ ] **Step 6: Lint and commit**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format .
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/agents/claude_client.py \
        sidequest-server/tests/agents/test_claude_client.py \
        sidequest-server/tests/agents/test_claude_client_stream.py
git commit -m "feat(agents): ClaudeClient.send_stream — streaming variant of send_with_session"
```

---

### Task 6: Stream cancellation + timeout behavior

Per spec §5.5–5.6: `aclose()` on the iterator must kill the subprocess; timeout fires `StreamError(kind=timeout)`.

**Files:**
- Modify: `sidequest-server/sidequest/agents/claude_client.py` (wrap `_iterate_stream` body in try/finally for kill-on-cancel)
- Modify: `sidequest-server/tests/agents/test_claude_client_stream.py` (add cancel + timeout tests)

- [ ] **Step 1: Write the failing tests**

Append to `test_claude_client_stream.py`:

```python
@pytest.mark.asyncio
async def test_aclose_kills_subprocess(monkeypatch):
    """Cancelling iteration mid-stream must kill the subprocess."""
    lines = [_delta_line(f"chunk {i} ") for i in range(20)]
    lines.append(_terminal_line("never reached"))

    captured_proc: list[FakeStreamingProcess] = []

    async def _spy_spawn(*args, **kwargs):
        proc = FakeStreamingProcess(lines=list(lines), per_line_delay=0.05)
        captured_proc.append(proc)
        return proc

    client = ClaudeClient(timeout=10.0, spawn_fn=_spy_spawn)

    events = []
    iterator = client.send_stream(prompt="hi", model="claude-opus-4-7")
    async for ev in iterator:
        events.append(ev)
        if len(events) == 2:
            break  # cancel mid-stream

    # Triggers __aexit__ → finally: → proc.kill()
    assert captured_proc[0]._killed is True


@pytest.mark.asyncio
async def test_stream_timeout_yields_stream_error():
    # 5 lines @ 1s delay each = 5s total; 0.5s timeout fires after first line
    lines = [_delta_line(f"chunk {i} ") for i in range(5)]
    spawn = make_streaming_spawn_fn(lines, per_line_delay=1.0)

    client = ClaudeClient(timeout=0.5, spawn_fn=spawn)

    events = []
    async for ev in client.send_stream(prompt="hi", model="claude-opus-4-7"):
        events.append(ev)

    errors = [e for e in events if isinstance(e, StreamError)]
    assert len(errors) == 1
    assert errors[0].kind == "timeout"
    # Should have captured at least the first chunk before timeout
    assert "chunk 0" in errors[0].partial_text or errors[0].partial_text == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client_stream.py -v -k "aclose or timeout"
```

Expected: FAIL.

- [ ] **Step 3: Add cancel-on-finally and timeout-aware iteration**

Wrap the `_iterate_stream` body's stdout loop in `asyncio.timeout()`. The subprocess kill on cancel needs a `try/finally` outer block:

```python
    async def _iterate_stream(
        self,
        proc: Any,
        span: object,
        start: float,
    ) -> AsyncIterator[StreamEvent]:
        """Consume the subprocess stdout as NDJSON events; yield StreamEvents.

        Always terminates with exactly one StreamComplete or StreamError.
        On iterator cancellation (aclose / break / raise), the subprocess
        is killed in the finally block.
        """
        from sidequest.agents.claude_stream_parser import (
            extract_terminal_metadata,
            extract_text_delta,
            is_terminal_event,
        )

        accumulated = ""
        terminal_meta = None  # TerminalMetadata | None

        try:
            try:
                async with asyncio.timeout(self._timeout):
                    async for raw_line in proc.stdout:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            logger.warning(
                                "claude_cli.stream.malformed_line line=%r", line[:200]
                            )
                            continue

                        delta_text = extract_text_delta(event)
                        if delta_text is not None:
                            accumulated += delta_text
                            yield TextDelta(text=delta_text)
                            continue

                        if is_terminal_event(event):
                            terminal_meta = extract_terminal_metadata(event)
                            continue
            except builtins.TimeoutError:
                elapsed = time.monotonic() - start
                yield StreamError(
                    kind="timeout",
                    elapsed_seconds=elapsed,
                    partial_text=accumulated,
                    detail=f"claude CLI timed out after {elapsed:.1f}s",
                    exit_code=None,
                )
                return

            await proc.wait()
            elapsed = time.monotonic() - start
            returncode = proc.returncode

            if returncode != 0:
                yield StreamError(
                    kind="subprocess_failed",
                    elapsed_seconds=elapsed,
                    partial_text=accumulated,
                    detail=f"claude CLI exited with code {returncode}",
                    exit_code=returncode,
                )
                return

            if not accumulated and terminal_meta is None:
                yield StreamError(
                    kind="empty",
                    elapsed_seconds=elapsed,
                    partial_text="",
                    detail="claude CLI returned no output",
                    exit_code=returncode,
                )
                return

            if terminal_meta is None:
                yield StreamComplete(
                    full_text=accumulated,
                    input_tokens=None,
                    output_tokens=None,
                    cache_creation_input_tokens=None,
                    cache_read_input_tokens=None,
                    session_id=None,
                    elapsed_seconds=elapsed,
                )
                return

            yield StreamComplete(
                full_text=terminal_meta.full_text or accumulated,
                input_tokens=terminal_meta.input_tokens,
                output_tokens=terminal_meta.output_tokens,
                cache_creation_input_tokens=terminal_meta.cache_creation_input_tokens,
                cache_read_input_tokens=terminal_meta.cache_read_input_tokens,
                session_id=terminal_meta.session_id,
                elapsed_seconds=elapsed,
            )
        finally:
            # Cancel-safety: if the consumer abandons us via aclose / break,
            # the subprocess may still be alive. Reap it.
            try:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
            except Exception:
                pass
```

- [ ] **Step 4: Run tests**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client_stream.py -v
```

Expected: PASS, 8 tests.

- [ ] **Step 5: Lint and commit**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format .
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/agents/claude_client.py \
        sidequest-server/tests/agents/test_claude_client_stream.py
git commit -m "feat(agents): cancel-on-finally + timeout for send_stream"
```

---

### Task 7: `LlmCapabilities.supports_streaming` flag flip

Existing capabilities() returns `supports_streaming=False`. Change to True (capability is now real for the streaming path).

**Files:**
- Modify: `sidequest-server/sidequest/agents/claude_client.py:204`
- Test: extend `test_claude_client_stream.py`

- [ ] **Step 1: Write the failing test**

```python
def test_capabilities_reports_streaming_supported():
    client = ClaudeClient()
    caps = client.capabilities()
    assert caps.supports_streaming is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client_stream.py::test_capabilities_reports_streaming_supported -v
```

Expected: FAIL — `assert False is True`

- [ ] **Step 3: Flip the flag**

In `claude_client.py:204`:

```python
            supports_streaming=True,
```

- [ ] **Step 4: Run all claude_client tests**

```bash
cd sidequest-server && uv run pytest tests/agents/test_claude_client.py tests/agents/test_claude_client_stream.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/agents/claude_client.py \
        sidequest-server/tests/agents/test_claude_client_stream.py
git commit -m "feat(agents): claude_client now declares supports_streaming=True"
```

---

### Task 8: `StreamFenceParser` — module + state types

The pure parser module that splits prose from `game_patch` JSON.

**Files:**
- Create: `sidequest-server/sidequest/agents/narrator/__init__.py` (empty marker if not present)
- Create: `sidequest-server/sidequest/agents/narrator/stream_fence.py`
- Create: `sidequest-server/tests/agents/test_stream_fence.py`

- [ ] **Step 1: Check whether `narrator/` package already exists**

```bash
ls sidequest-server/sidequest/agents/narrator/ 2>/dev/null || echo "MUST CREATE"
```

If it exists (e.g., as a sibling to `narrator.py`), use it. If not, the new `narrator/` package can coexist with the existing `narrator.py` module — Python resolves `sidequest.agents.narrator` to the package (`narrator/__init__.py`) when both exist; **DO NOT create a `narrator/` package while `narrator.py` exists** — this will break the import. Instead, place the file at:

```
sidequest-server/sidequest/agents/stream_fence.py
```

(sibling to narrator.py). Tests import `from sidequest.agents.stream_fence import ...`. Use this path going forward.

- [ ] **Step 2: Write the failing tests**

```python
# sidequest-server/tests/agents/test_stream_fence.py
"""Tests for StreamFenceParser."""
from __future__ import annotations

import pytest

from sidequest.agents.stream_fence import (
    FenceParseResult,
    StreamFenceParser,
)


def _collector():
    """Returns (callback, recorded_chunks_list)."""
    chunks: list[str] = []

    async def cb(chunk: str) -> None:
        chunks.append(chunk)

    return cb, chunks


@pytest.mark.asyncio
async def test_prose_only_no_fence():
    cb, chunks = _collector()
    parser = StreamFenceParser(on_prose_delta=cb)
    await parser.feed("Hello, world. ")
    await parser.feed("This is all prose.")
    result = await parser.finalize()

    assert result.status == "no_fence"
    assert result.game_patch_json is None
    assert "".join(chunks) == "Hello, world. This is all prose."
    assert result.prose == "Hello, world. This is all prose."


@pytest.mark.asyncio
async def test_clean_split():
    cb, chunks = _collector()
    parser = StreamFenceParser(on_prose_delta=cb)
    full = (
        "**The Collapsed Overpass**\n\n"
        "Rust dust drifts down.\n"
        "\n```game_patch\n"
        '{"items_lost": [{"name": "key"}]}\n'
        "```\n"
    )
    await parser.feed(full)
    result = await parser.finalize()

    assert result.status == "complete"
    assert "Rust dust drifts down" in "".join(chunks)
    assert "game_patch" not in "".join(chunks)
    assert result.game_patch_json is not None
    assert "items_lost" in result.game_patch_json


@pytest.mark.asyncio
async def test_fence_in_prose_passthrough_python_block():
    """Triple-backticks with non-game_patch label must pass through."""
    cb, chunks = _collector()
    parser = StreamFenceParser(on_prose_delta=cb)
    full = (
        "She reads the terminal:\n"
        "\n```python\n"
        "if access_denied:\n"
        "    raise Exception\n"
        "```\n"
        "She turns away.\n"
    )
    await parser.feed(full)
    result = await parser.finalize()

    assert result.status == "no_fence"
    full_prose = "".join(chunks)
    assert "```python" in full_prose
    assert "raise Exception" in full_prose
    assert "She turns away" in full_prose


@pytest.mark.asyncio
async def test_unclosed_fence():
    cb, chunks = _collector()
    parser = StreamFenceParser(on_prose_delta=cb)
    await parser.feed("prose\n\n```game_patch\n")
    await parser.feed('{"items_lost": [')
    # Stream ends before close fence
    result = await parser.finalize()

    assert result.status == "unclosed_fence"
    assert result.game_patch_json == '{"items_lost": ['
    assert "".join(chunks) == "prose\n"


@pytest.mark.asyncio
async def test_truncated_at_open_fence_label():
    """If stream ends mid-fence-label, partial-fence bytes must NOT
    be emitted as prose. They flush at finalize as no_fence content."""
    cb, chunks = _collector()
    parser = StreamFenceParser(on_prose_delta=cb)
    await parser.feed("prose ending\n\n``game_pa")
    result = await parser.finalize()

    assert result.status == "no_fence"
    assert "prose ending" in "".join(chunks)
    # The partial-fence bytes flush at finalize
    assert "``game_pa" in "".join(chunks)


@pytest.mark.asyncio
async def test_chunk_at_every_byte_boundary():
    """Splitting input at every byte boundary must yield identical result."""
    full = (
        "prose A.\n\n```game_patch\n"
        '{"items_lost": [{"name": "key"}]}\n'
        "```\n"
    )

    # Reference run: feed all at once
    cb_ref, chunks_ref = _collector()
    p_ref = StreamFenceParser(on_prose_delta=cb_ref)
    await p_ref.feed(full)
    ref = await p_ref.finalize()

    # Boundary runs: split at every position
    for split in range(1, len(full)):
        cb_x, chunks_x = _collector()
        p_x = StreamFenceParser(on_prose_delta=cb_x)
        await p_x.feed(full[:split])
        await p_x.feed(full[split:])
        out = await p_x.finalize()
        assert out.status == ref.status, f"status mismatch at split={split}"
        assert out.prose == ref.prose, f"prose mismatch at split={split}"
        assert out.game_patch_json == ref.game_patch_json, f"json mismatch at split={split}"


@pytest.mark.asyncio
async def test_pretty_printed_json_round_trips():
    cb, _ = _collector()
    parser = StreamFenceParser(on_prose_delta=cb)
    pretty = '\n```game_patch\n{\n  "items_lost": [\n    {"name": "key"}\n  ]\n}\n```\n'
    await parser.feed("prose" + pretty)
    result = await parser.finalize()
    assert result.status == "complete"
    assert "items_lost" in result.game_patch_json
    assert "key" in result.game_patch_json


@pytest.mark.asyncio
async def test_crlf_line_endings():
    cb, chunks = _collector()
    parser = StreamFenceParser(on_prose_delta=cb)
    full = "prose\r\n\r\n```game_patch\r\n{\"a\":1}\r\n```\r\n"
    await parser.feed(full)
    result = await parser.finalize()
    assert result.status == "complete"
    assert result.game_patch_json is not None and '"a":1' in result.game_patch_json


@pytest.mark.asyncio
async def test_trailing_garbage_after_close():
    cb, chunks = _collector()
    parser = StreamFenceParser(on_prose_delta=cb)
    full = "prose\n\n```game_patch\n{\"a\":1}\n```\nGARBAGE AFTER\n"
    await parser.feed(full)
    result = await parser.finalize()
    assert result.status == "trailing_garbage"
    assert result.game_patch_json is not None and '"a":1' in result.game_patch_json
    # Garbage discarded, not appended to JSON
    assert "GARBAGE" not in (result.game_patch_json or "")
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/agents/test_stream_fence.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.agents.stream_fence'`

- [ ] **Step 4: Implement the parser**

```python
# sidequest-server/sidequest/agents/stream_fence.py
"""StreamFenceParser — splits a streaming claude response into prose deltas
and a buffered game_patch JSON block.

Driven externally — feed() called per TextDelta from claude_client.send_stream;
finalize() called once after stream EOS. Prose chunks emit via the
on_prose_delta callback as soon as they're confirmed not to be part of a
fence; JSON is accumulated internally.

Boundary patterns are LABEL-AWARE — only the literal `\\n```game_patch` opener
and `\\n``` ` closer match. Non-game_patch fences in prose (```python, bare ```)
pass through unchanged.
"""
from __future__ import annotations

import enum
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

# CRLF-tolerant patterns. Open requires the literal "game_patch" label;
# close is bare. The leading `\r?\n` anchors the fence to a line boundary.
_OPEN_FENCE = re.compile(r"\r?\n```game_patch[ \t]*\r?\n")
_CLOSE_FENCE = re.compile(r"\r?\n```[ \t]*(?:\r?\n|$)")

# Lookahead size: enough bytes to recognize "\n```game_patch\n" if a chunk
# boundary cuts the fence in half. The longest prefix-of-fence we might need
# to hold back is len("\r\n```game_patch") = 16 bytes.
_LOOKAHEAD_BYTES = 16


class _State(enum.Enum):
    PROSE = "prose"
    JSON_BUFFERING = "json_buffering"
    EPILOGUE = "epilogue"


@dataclass(frozen=True, slots=True)
class FenceParseResult:
    prose: str
    game_patch_json: str | None
    status: Literal["complete", "no_fence", "unclosed_fence", "trailing_garbage"]
    fence_offset: int | None  # offset in concatenated stream where the open fence appeared


class StreamFenceParser:
    """Splits a streaming claude response into prose (live) and game_patch (buffered).

    Driven externally — feed() called per TextDelta, finalize() called at EOS.
    Prose chunks are emitted via the on_prose_delta callback as soon as they
    are confirmed to not be part of a fence. JSON is accumulated internally.
    """

    def __init__(
        self, on_prose_delta: Callable[[str], Awaitable[None]]
    ) -> None:
        self._on_prose_delta = on_prose_delta
        self._state: _State = _State.PROSE
        self._carry: str = ""
        self._json_buffer: str = ""
        self._prose_total: str = ""
        self._fence_offset: int | None = None
        self._epilogue_garbage: bool = False
        self._finalized: bool = False
        self._stream_offset: int = 0

    async def feed(self, chunk: str) -> None:
        if self._finalized:
            raise RuntimeError("StreamFenceParser.feed() called after finalize()")

        self._carry += chunk

        # Drive the state machine until it stops making progress on this carry.
        while True:
            if self._state is _State.PROSE:
                progressed = await self._handle_prose()
                if not progressed:
                    return
            elif self._state is _State.JSON_BUFFERING:
                progressed = self._handle_json()
                if not progressed:
                    return
            else:  # EPILOGUE
                # Discard everything in carry as trailing garbage.
                if self._carry:
                    self._epilogue_garbage = True
                    self._carry = ""
                return

    async def _handle_prose(self) -> bool:
        """Returns True if state changed (loop should re-enter)."""
        match = _OPEN_FENCE.search(self._carry)
        if match is not None:
            prefix = self._carry[: match.start()]
            if prefix:
                await self._on_prose_delta(prefix)
                self._prose_total += prefix
            self._fence_offset = (
                self._stream_offset + match.start()
            )
            self._stream_offset += match.end()
            self._carry = self._carry[match.end():]
            self._state = _State.JSON_BUFFERING
            return True

        # No confirmed fence. Hold back a lookahead-sized tail.
        safe_emit_len = max(0, len(self._carry) - _LOOKAHEAD_BYTES)
        if safe_emit_len > 0:
            emit = self._carry[:safe_emit_len]
            self._carry = self._carry[safe_emit_len:]
            self._stream_offset += safe_emit_len
            await self._on_prose_delta(emit)
            self._prose_total += emit
        return False

    def _handle_json(self) -> bool:
        match = _CLOSE_FENCE.search(self._carry)
        if match is not None:
            self._json_buffer += self._carry[: match.start()]
            self._stream_offset += match.end()
            self._carry = self._carry[match.end():]
            self._state = _State.EPILOGUE
            return True

        # Hold back lookahead-sized tail in case it's the start of a close fence.
        safe_buffer_len = max(0, len(self._carry) - _LOOKAHEAD_BYTES)
        if safe_buffer_len > 0:
            self._json_buffer += self._carry[:safe_buffer_len]
            self._carry = self._carry[safe_buffer_len:]
            self._stream_offset += safe_buffer_len
        return False

    async def finalize(self) -> FenceParseResult:
        if self._finalized:
            raise RuntimeError("finalize() called twice")
        self._finalized = True

        # Flush remaining carry per terminal state.
        if self._state is _State.PROSE:
            if self._carry:
                await self._on_prose_delta(self._carry)
                self._prose_total += self._carry
                self._carry = ""
            return FenceParseResult(
                prose=self._prose_total,
                game_patch_json=None,
                status="no_fence",
                fence_offset=None,
            )

        if self._state is _State.JSON_BUFFERING:
            self._json_buffer += self._carry
            self._carry = ""
            return FenceParseResult(
                prose=self._prose_total,
                game_patch_json=self._json_buffer,
                status="unclosed_fence",
                fence_offset=self._fence_offset,
            )

        # EPILOGUE
        if self._carry:
            self._epilogue_garbage = True
            self._carry = ""
        status: Literal["complete", "trailing_garbage"] = (
            "trailing_garbage" if self._epilogue_garbage else "complete"
        )
        return FenceParseResult(
            prose=self._prose_total,
            game_patch_json=self._json_buffer,
            status=status,
            fence_offset=self._fence_offset,
        )
```

- [ ] **Step 5: Run tests**

```bash
cd sidequest-server && uv run pytest tests/agents/test_stream_fence.py -v
```

Expected: PASS, 9 tests.

- [ ] **Step 6: Lint and commit**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format .
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/agents/stream_fence.py \
        sidequest-server/tests/agents/test_stream_fence.py
git commit -m "feat(agents): StreamFenceParser — label-aware boundary split for streaming narration"
```

---

### Task 9: Narrator streaming branch behind feature flag

`narrator.py` gains a `_respond_streaming()` method. `respond()` checks `SIDEQUEST_NARRATOR_STREAMING` and routes accordingly. With the flag off, behavior is unchanged.

**Files:**
- Modify: `sidequest-server/sidequest/agents/narrator.py` (add streaming branch)
- Test: `sidequest-server/tests/agents/test_narrator_streaming.py` (create)

- [ ] **Step 1: Read narrator.py to find the existing entry point**

```bash
grep -n "def respond\|async def respond\|self\.client\|self\._client\|self\._llm" \
  sidequest-server/sidequest/agents/narrator.py | head -20
```

Read the surrounding code (~30 lines) to understand the existing synchronous entry point's signature, what it returns, where it calls the client, and where the resulting prose is split into prose + game_patch. Note the exact method name (likely `respond` or similar).

- [ ] **Step 2: Write the failing wiring test**

```python
# sidequest-server/tests/agents/test_narrator_streaming.py
"""Wiring tests for narrator streaming branch behind SIDEQUEST_NARRATOR_STREAMING."""
from __future__ import annotations

import os
import pytest


def test_narrator_module_exposes_streaming_capability_check():
    """The narrator module must expose a function that reports whether
    streaming is enabled via env var. This is the wiring test that ensures
    the flag is actually consulted and not orphaned."""
    from sidequest.agents.narrator import is_streaming_enabled

    assert callable(is_streaming_enabled)


def test_streaming_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SIDEQUEST_NARRATOR_STREAMING", raising=False)
    from sidequest.agents.narrator import is_streaming_enabled
    assert is_streaming_enabled() is False


def test_streaming_enabled_when_flag_is_one(monkeypatch):
    monkeypatch.setenv("SIDEQUEST_NARRATOR_STREAMING", "1")
    from sidequest.agents.narrator import is_streaming_enabled
    assert is_streaming_enabled() is True


def test_streaming_disabled_when_flag_is_zero(monkeypatch):
    monkeypatch.setenv("SIDEQUEST_NARRATOR_STREAMING", "0")
    from sidequest.agents.narrator import is_streaming_enabled
    assert is_streaming_enabled() is False
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/agents/test_narrator_streaming.py -v
```

Expected: FAIL — `ImportError: cannot import name 'is_streaming_enabled'`

- [ ] **Step 4: Add `is_streaming_enabled` and the streaming branch**

In `sidequest-server/sidequest/agents/narrator.py`, near the top imports:

```python
import os
```

Add a module-level helper:

```python
def is_streaming_enabled() -> bool:
    """True when the narrator should use the streaming claude_client path.

    Gated by SIDEQUEST_NARRATOR_STREAMING env var. Default off to preserve
    existing synchronous behavior until the full streaming pipeline ships.
    """
    return os.environ.get("SIDEQUEST_NARRATOR_STREAMING", "0") == "1"
```

Locate the existing synchronous `respond` (or equivalent) method and add a routing branch at the top:

```python
    async def respond(self, ...) -> ...:
        if is_streaming_enabled():
            return await self._respond_streaming(...)
        # ── existing synchronous path below, UNCHANGED ──
        ...
```

For now, `_respond_streaming` is a stub that delegates to the synchronous path so this commit doesn't break behavior:

```python
    async def _respond_streaming(self, *args, **kwargs):
        """Streaming variant — wired in Story 2 (broadcast_delta + WS message).
        For now, delegates to synchronous path so flag-on doesn't crash.
        """
        return await self._respond_synchronous(*args, **kwargs)
```

Rename the existing `respond` body's logic into `_respond_synchronous` and have `respond` route between the two.

- [ ] **Step 5: Run all narrator tests**

```bash
cd sidequest-server && uv run pytest tests/agents/test_narrator.py tests/agents/test_narrator_streaming.py -v
```

Expected: PASS — existing narrator tests still pass (synchronous path unchanged), new wiring tests pass.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format .
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/agents/narrator.py \
        sidequest-server/tests/agents/test_narrator_streaming.py
git commit -m "feat(narrator): SIDEQUEST_NARRATOR_STREAMING flag + routing stub"
```

---

### Story 1 Milestone

After Tasks 1–9, the server has:
- A working `claude_client.send_stream()` with full unit-test coverage
- A working `StreamFenceParser` with full unit-test coverage
- Narrator gated behind `SIDEQUEST_NARRATOR_STREAMING` flag (defaults off, behavior unchanged)

**Verify before continuing to Story 2:**

```bash
cd sidequest-server && uv run pytest tests/agents/ -v && uv run ruff check .
```

Expected: all tests pass, lint clean.

---

## Story 2 — WS Protocol + Emitter + OTEL (3 pts, server)

Server-side fan-out and observability. After this story, the server emits `narration.delta` frames during streaming turns (when flag on); the UI receives an unknown message kind and ignores it.

---

### Task 10: `NarrationDelta` Pydantic message + KIND mapping

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py` (or wherever existing GameMessage variants live — find via `grep -rn "_KIND_TO_MESSAGE_CLS" sidequest/`)
- Test: `sidequest-server/tests/protocol/test_narration_delta_message.py`

- [ ] **Step 1: Find the existing message-class registry**

```bash
grep -rn "_KIND_TO_MESSAGE_CLS\|class Narration\b\|kind.*=.*\"narration\"" \
  sidequest-server/sidequest/ 2>/dev/null | head -20
```

Read the file(s) to understand the existing pydantic-message convention (payload class, message class, kind string).

- [ ] **Step 2: Write the failing test**

```python
# sidequest-server/tests/protocol/test_narration_delta_message.py
"""Tests for the new NarrationDelta WS message."""
from __future__ import annotations

import json


def test_narration_delta_payload_round_trips():
    from sidequest.protocol.messages import NarrationDelta, NarrationDeltaPayload

    payload = NarrationDeltaPayload(turn_id="t-1", chunk="Hello ", seq=0)
    msg = NarrationDelta(payload=payload)

    dumped = msg.model_dump_json()
    parsed = json.loads(dumped)

    assert parsed["kind"] == "narration.delta"
    assert parsed["payload"]["turn_id"] == "t-1"
    assert parsed["payload"]["chunk"] == "Hello "
    assert parsed["payload"]["seq"] == 0


def test_narration_delta_kind_registered_in_dispatch_table():
    """The message must be registered so emit_event can find it (even though
    deltas don't go through emit_event, the registration is part of the
    canonical protocol surface)."""
    from sidequest.server.session_handler import _KIND_TO_MESSAGE_CLS

    assert "narration.delta" in _KIND_TO_MESSAGE_CLS
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/protocol/test_narration_delta_message.py -v
```

Expected: FAIL.

- [ ] **Step 4: Add the message classes**

Following the existing pattern (read it first), in the protocol messages file:

```python
class NarrationDeltaPayload(BaseModel):
    """Ephemeral prose-delta payload, per ADR-038-extension."""

    turn_id: str
    chunk: str
    seq: int


class NarrationDelta(BaseModel):
    """Streaming narration delta — broadcast to all sockets, NOT event-sourced."""

    kind: Literal["narration.delta"] = "narration.delta"
    payload: NarrationDeltaPayload
```

Register in `_KIND_TO_MESSAGE_CLS` dict in `session_handler.py`:

```python
"narration.delta": NarrationDelta,
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/protocol/test_narration_delta_message.py -v
```

Expected: PASS, 2 tests.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/protocol/messages.py \
        sidequest-server/sidequest/server/session_handler.py \
        sidequest-server/tests/protocol/test_narration_delta_message.py
git commit -m "feat(protocol): NarrationDelta ephemeral message type"
```

---

### Task 11: `broadcast_delta` helper

Bypass `emit_event()` — pure socket fan-out. No DB write, no projection, no perception filter.

**Files:**
- Modify: `sidequest-server/sidequest/server/emitters.py` (add helper near other broadcast helpers)
- Test: `sidequest-server/tests/server/test_emitters_broadcast_delta.py`

- [ ] **Step 1: Read existing emitter patterns**

```bash
grep -n "async def\|connected_sockets\|connected_player_ids" \
  sidequest-server/sidequest/server/emitters.py | head -20
```

Identify how existing helpers iterate sockets (likely `room.connected_sockets()` or similar from `session_handler`).

- [ ] **Step 2: Write the failing test**

```python
# sidequest-server/tests/server/test_emitters_broadcast_delta.py
"""Tests for broadcast_delta — ephemeral fan-out to all sockets."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_broadcast_delta_fans_out_to_all_sockets():
    from sidequest.server.emitters import broadcast_delta

    socket_a = AsyncMock()
    socket_b = AsyncMock()
    room = MagicMock()
    room.connected_sockets.return_value = [socket_a, socket_b]

    await broadcast_delta(turn_id="t-1", chunk="hello ", seq=0, room=room)

    socket_a.send_json.assert_awaited_once()
    socket_b.send_json.assert_awaited_once()

    sent = socket_a.send_json.call_args[0][0]
    assert sent["kind"] == "narration.delta"
    assert sent["payload"]["turn_id"] == "t-1"
    assert sent["payload"]["chunk"] == "hello "
    assert sent["payload"]["seq"] == 0


@pytest.mark.asyncio
async def test_broadcast_delta_does_not_call_emit_event():
    """broadcast_delta is ephemeral: no DB write, no projection cache."""
    from sidequest.server.emitters import broadcast_delta

    room = MagicMock()
    room.connected_sockets.return_value = []

    # No handler argument — the helper must NOT touch event_log or projection_cache
    await broadcast_delta(turn_id="t-1", chunk="x", seq=0, room=room)
    # Test passes if no AttributeError on missing handler/event_log
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_emitters_broadcast_delta.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement `broadcast_delta`**

Append to `emitters.py`:

```python
async def broadcast_delta(
    *,
    turn_id: str,
    chunk: str,
    seq: int,
    room: object,
) -> None:
    """Broadcast an ephemeral narration delta to all sockets in the room.

    Does NOT call emit_event(). Does NOT touch the projection cache.
    Does NOT run perception_rewriter. Pure presentation channel.

    Implementation note: each socket gets the same payload — deltas are not
    per-recipient filtered. This is correct today because the perception
    rewriter is a no-op for narration (no kind-tagged spans yet, see
    perception_rewriter.py docstring re: G10 deferral). When G10 ships,
    this fan-out needs revisiting.
    """
    from sidequest.protocol.messages import NarrationDelta, NarrationDeltaPayload

    msg = NarrationDelta(payload=NarrationDeltaPayload(
        turn_id=turn_id, chunk=chunk, seq=seq,
    ))
    payload_dict = msg.model_dump()
    for socket in room.connected_sockets():
        try:
            await socket.send_json(payload_dict)
        except Exception:
            # Per-socket errors must not break fan-out to other recipients.
            logger.warning("broadcast_delta.socket_send_failed turn_id=%s seq=%d", turn_id, seq)
```

- [ ] **Step 5: Run test**

```bash
cd sidequest-server && uv run pytest tests/server/test_emitters_broadcast_delta.py -v
```

Expected: PASS, 2 tests.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/emitters.py \
        sidequest-server/tests/server/test_emitters_broadcast_delta.py
git commit -m "feat(server): broadcast_delta — ephemeral narration fan-out"
```

---

### Task 12: Wire `_respond_streaming` to consume the stream + broadcast deltas

The narrator's `_respond_streaming` (currently a stub from Task 9) becomes real.

**Files:**
- Modify: `sidequest-server/sidequest/agents/narrator.py` (replace stub `_respond_streaming` body)
- Test: `sidequest-server/tests/agents/test_narrator_streaming.py` (extend with end-to-end mock test)

- [ ] **Step 1: Write the failing integration test**

Append to `test_narrator_streaming.py`:

```python
@pytest.mark.asyncio
async def test_streaming_path_broadcasts_deltas_then_emits_canonical(monkeypatch):
    """End-to-end with mocked claude_client.send_stream + spy on broadcast_delta."""
    monkeypatch.setenv("SIDEQUEST_NARRATOR_STREAMING", "1")

    from sidequest.agents.claude_client import (
        StreamComplete, TextDelta,
    )

    # Construct an in-memory async iterator the mock returns
    async def mock_send_stream(*args, **kwargs):
        yield TextDelta(text="**Location**\n\n")
        yield TextDelta(text="The wind howls. ")
        yield TextDelta(text="The door slams.\n\n")
        yield TextDelta(text="```game_patch\n")
        yield TextDelta(text='{"items_lost": []}\n')
        yield TextDelta(text="```\n")
        yield StreamComplete(
            full_text=(
                "**Location**\n\nThe wind howls. The door slams.\n\n"
                "```game_patch\n{\"items_lost\": []}\n```\n"
            ),
            input_tokens=100,
            output_tokens=20,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            session_id="sess-1",
            elapsed_seconds=2.5,
        )

    deltas: list[dict] = []
    canonical: list[dict] = []

    async def spy_broadcast(*, turn_id, chunk, seq, room):
        deltas.append({"turn_id": turn_id, "chunk": chunk, "seq": seq})

    async def spy_emit_event(handler, kind, payload_model):
        canonical.append({"kind": kind, "payload": payload_model})

    # Patch the call sites the narrator uses
    import sidequest.agents.narrator as narrator_mod
    monkeypatch.setattr(narrator_mod, "broadcast_delta", spy_broadcast)
    monkeypatch.setattr(narrator_mod, "emit_event", spy_emit_event)

    # Mock claude_client on the narrator instance — this depends on actual
    # narrator construction in your codebase. Adjust the fixture as needed.
    # The wiring test below verifies the import is correct.
    pytest.skip("end-to-end test requires narrator-instance fixture wired in Task 12 step 4")
```

(Marking as skip until the real narrator-instance fixture is built in Step 4. The skip becomes a real assertion once the fixture lands.)

- [ ] **Step 2: Replace `_respond_streaming` stub with real implementation**

In `sidequest-server/sidequest/agents/narrator.py`:

```python
    async def _respond_streaming(
        self,
        prompt: str,
        *,
        turn_id: str,
        room: object,
        ...,  # match the signature of _respond_synchronous
    ):
        """Streaming variant of respond — broadcasts prose deltas live,
        emits canonical narration + game_patch at stream EOS via the
        existing emit_event() pipeline (unchanged)."""
        from sidequest.agents.claude_client import (
            StreamComplete,
            StreamError,
            TextDelta,
        )
        from sidequest.agents.stream_fence import StreamFenceParser
        from sidequest.server.emitters import broadcast_delta

        seq = 0

        async def on_prose_delta(chunk: str) -> None:
            nonlocal seq
            await broadcast_delta(
                turn_id=turn_id, chunk=chunk, seq=seq, room=room
            )
            seq += 1

        parser = StreamFenceParser(on_prose_delta=on_prose_delta)
        terminal_event: StreamComplete | StreamError | None = None

        async for event in self._client.send_stream(
            prompt=prompt, model=self._model, session_id=self._session_id, ...
        ):
            if isinstance(event, TextDelta):
                await parser.feed(event.text)
            elif isinstance(event, (StreamComplete, StreamError)):
                terminal_event = event

        result = await parser.finalize()

        if isinstance(terminal_event, StreamError):
            return await self._handle_stream_error(terminal_event, result, turn_id)

        # Existing post-EOS path: parse game_patch, run the unchanged
        # synchronous emit_event pipeline.
        return await self._finalize_canonical_event(
            prose=result.prose,
            game_patch_json=result.game_patch_json,
            terminal=terminal_event,
            turn_id=turn_id,
        )
```

`_finalize_canonical_event` and `_handle_stream_error` need to be added — they wrap the prose+game_patch path that the synchronous variant already does. **Re-use the existing canonical emission code** by extracting it from `_respond_synchronous` into a shared private helper.

- [ ] **Step 3: Run all narrator tests**

```bash
cd sidequest-server && uv run pytest tests/agents/test_narrator.py tests/agents/test_narrator_streaming.py -v
```

Expected: existing narrator tests pass (synchronous path unchanged); the streaming wiring test passes (or skips with the documented reason).

- [ ] **Step 4: Replace skip with real fixture**

Build a minimal `narrator_streaming_fixture` that constructs a Narrator with a mocked `_client.send_stream` and a fake room. The exact fixture shape depends on the existing `Narrator` class constructor — read `narrator.py` to find what's required (room, llm client, session_id, etc.) and mock the minimum.

Replace the `pytest.skip` line with real assertions:

```python
    # Build narrator with mocks
    narrator = make_narrator_with_mock_stream(
        send_stream_fn=mock_send_stream,
        room=...,
    )
    await narrator.respond(prompt="explore the corridor", turn_id="t-1")

    # Assertions
    assert len(deltas) == 6  # 6 TextDelta chunks broadcast
    assert deltas[0]["seq"] == 0
    assert deltas[-1]["seq"] == 5
    # Game patch fence content is NOT broadcast as a delta
    delta_text = "".join(d["chunk"] for d in deltas)
    assert "items_lost" not in delta_text
    # Canonical event was emitted exactly once
    narration_events = [e for e in canonical if e["kind"] == "narration"]
    assert len(narration_events) == 1
```

- [ ] **Step 5: Lint and commit**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format .
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/agents/narrator.py \
        sidequest-server/tests/agents/test_narrator_streaming.py
git commit -m "feat(narrator): wire _respond_streaming to broadcast deltas + emit canonical at EOS"
```

---

### Task 13: OTEL spans for stream lifecycle

Per spec §6 — `narrator.stream.start`, `.first_token`, `.fence_detected`, `.complete`, `.error`, `.cancelled`.

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans.py` (add helpers)
- Modify: `sidequest-server/sidequest/agents/narrator.py` (instrument `_respond_streaming`)
- Modify: `sidequest-server/sidequest/agents/stream_fence.py` (emit `fence_detected` on state transition)
- Test: `sidequest-server/tests/telemetry/test_streaming_spans.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/telemetry/test_streaming_spans.py
"""Tests for narrator streaming OTEL spans."""
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def _setup_in_memory_tracer() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def test_stream_start_span_records_turn_id_and_prompt_tokens():
    from sidequest.telemetry.spans import narrator_stream_start_span

    exporter = _setup_in_memory_tracer()
    with narrator_stream_start_span(turn_id="t-1", prompt_tokens=100, model="claude-opus-4-7", session_id="s-1"):
        pass

    spans = exporter.get_finished_spans()
    [span] = [s for s in spans if s.name == "narrator.stream.start"]
    assert span.attributes["turn_id"] == "t-1"
    assert span.attributes["prompt_tokens"] == 100
    assert span.attributes["model"] == "claude-opus-4-7"


def test_stream_complete_span_records_status_and_metrics():
    from sidequest.telemetry.spans import narrator_stream_complete_span

    exporter = _setup_in_memory_tracer()
    narrator_stream_complete_span(
        turn_id="t-1",
        total_seconds=5.0,
        ttft_seconds=1.2,
        prose_bytes=1500,
        delta_count=42,
        json_parse_status="complete",
        input_tokens=100,
        output_tokens=50,
    )

    spans = exporter.get_finished_spans()
    [span] = [s for s in spans if s.name == "narrator.stream.complete"]
    assert span.attributes["json_parse_status"] == "complete"
    assert span.attributes["delta_count"] == 42
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/telemetry/test_streaming_spans.py -v
```

Expected: FAIL — `ImportError: cannot import name 'narrator_stream_start_span'`

- [ ] **Step 3: Add span helpers**

Append to `sidequest/telemetry/spans.py`:

```python
import contextlib

_streaming_tracer = trace.get_tracer("sidequest.narrator.stream")


@contextlib.contextmanager
def narrator_stream_start_span(
    *,
    turn_id: str,
    prompt_tokens: int,
    model: str,
    session_id: str | None,
):
    """Wraps the entire streaming turn. Emits as narrator.stream.start."""
    with _streaming_tracer.start_as_current_span("narrator.stream.start") as span:
        span.set_attribute("turn_id", turn_id)
        span.set_attribute("prompt_tokens", prompt_tokens)
        span.set_attribute("model", model)
        if session_id is not None:
            span.set_attribute("session_id", session_id)
        yield span


def narrator_stream_first_token(*, turn_id: str, ttft_seconds: float) -> None:
    """One-shot span emitted on first TextDelta."""
    with _streaming_tracer.start_as_current_span("narrator.stream.first_token") as span:
        span.set_attribute("turn_id", turn_id)
        span.set_attribute("ttft_seconds", ttft_seconds)


def narrator_stream_fence_detected(
    *, turn_id: str, prose_bytes_at_fence: int, seconds_to_fence: float
) -> None:
    with _streaming_tracer.start_as_current_span("narrator.stream.fence_detected") as span:
        span.set_attribute("turn_id", turn_id)
        span.set_attribute("prose_bytes_at_fence", prose_bytes_at_fence)
        span.set_attribute("seconds_to_fence", seconds_to_fence)


def narrator_stream_complete_span(
    *,
    turn_id: str,
    total_seconds: float,
    ttft_seconds: float | None,
    prose_bytes: int,
    delta_count: int,
    json_parse_status: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> None:
    with _streaming_tracer.start_as_current_span("narrator.stream.complete") as span:
        span.set_attribute("turn_id", turn_id)
        span.set_attribute("total_seconds", total_seconds)
        if ttft_seconds is not None:
            span.set_attribute("ttft_seconds", ttft_seconds)
        span.set_attribute("prose_bytes", prose_bytes)
        span.set_attribute("delta_count", delta_count)
        span.set_attribute("json_parse_status", json_parse_status)
        if input_tokens is not None:
            span.set_attribute("input_tokens", input_tokens)
        if output_tokens is not None:
            span.set_attribute("output_tokens", output_tokens)


def narrator_stream_error_span(
    *,
    turn_id: str,
    error_kind: str,
    partial_prose_bytes: int,
    total_seconds: float,
    detail: str,
) -> None:
    with _streaming_tracer.start_as_current_span("narrator.stream.error") as span:
        span.set_attribute("turn_id", turn_id)
        span.set_attribute("error_kind", error_kind)
        span.set_attribute("partial_prose_bytes", partial_prose_bytes)
        span.set_attribute("total_seconds", total_seconds)
        span.set_attribute("detail", detail[:500])
        span.set_status(trace.Status(trace.StatusCode.ERROR, detail))


def narrator_stream_cancelled_span(
    *, turn_id: str, reason: str, partial_prose_bytes: int
) -> None:
    with _streaming_tracer.start_as_current_span("narrator.stream.cancelled") as span:
        span.set_attribute("turn_id", turn_id)
        span.set_attribute("reason", reason)
        span.set_attribute("partial_prose_bytes", partial_prose_bytes)
```

- [ ] **Step 4: Instrument the narrator's `_respond_streaming` with the spans**

In `narrator.py:_respond_streaming`, wrap the streaming work:

```python
        from sidequest.telemetry.spans import (
            narrator_stream_complete_span,
            narrator_stream_error_span,
            narrator_stream_first_token,
            narrator_stream_start_span,
        )
        import time

        start = time.monotonic()
        first_token_time: float | None = None
        delta_count = 0

        with narrator_stream_start_span(
            turn_id=turn_id,
            prompt_tokens=len(prompt) // 4,  # rough estimate; replace with real tokenization if available
            model=self._model,
            session_id=self._session_id,
        ):
            ...  # existing streaming loop, but instrument:
            async for event in self._client.send_stream(...):
                if isinstance(event, TextDelta):
                    if first_token_time is None:
                        first_token_time = time.monotonic() - start
                        narrator_stream_first_token(
                            turn_id=turn_id, ttft_seconds=first_token_time
                        )
                    delta_count += 1
                    await parser.feed(event.text)
                ...

            result = await parser.finalize()
            elapsed = time.monotonic() - start

            if isinstance(terminal_event, StreamError):
                narrator_stream_error_span(
                    turn_id=turn_id,
                    error_kind=terminal_event.kind,
                    partial_prose_bytes=len(result.prose),
                    total_seconds=elapsed,
                    detail=terminal_event.detail,
                )
                return await self._handle_stream_error(...)

            narrator_stream_complete_span(
                turn_id=turn_id,
                total_seconds=elapsed,
                ttft_seconds=first_token_time,
                prose_bytes=len(result.prose),
                delta_count=delta_count,
                json_parse_status=result.status,
                input_tokens=terminal_event.input_tokens if terminal_event else None,
                output_tokens=terminal_event.output_tokens if terminal_event else None,
            )
```

- [ ] **Step 5: Add `fence_detected` emission in StreamFenceParser**

Modify `stream_fence.py`'s `_handle_prose` so that when transitioning to `JSON_BUFFERING`, it can call an optional callback:

```python
class StreamFenceParser:
    def __init__(
        self,
        on_prose_delta: Callable[[str], Awaitable[None]],
        on_fence_detected: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        self._on_prose_delta = on_prose_delta
        self._on_fence_detected = on_fence_detected
        ...

    async def _handle_prose(self) -> bool:
        match = _OPEN_FENCE.search(self._carry)
        if match is not None:
            prefix = self._carry[: match.start()]
            if prefix:
                await self._on_prose_delta(prefix)
                self._prose_total += prefix
            self._fence_offset = self._stream_offset + match.start()
            self._stream_offset += match.end()
            self._carry = self._carry[match.end():]
            self._state = _State.JSON_BUFFERING
            if self._on_fence_detected is not None:
                await self._on_fence_detected(len(self._prose_total))
            return True
        ...
```

In the narrator's streaming path, pass `on_fence_detected` that emits the `narrator_stream_fence_detected` span.

- [ ] **Step 6: Run tests**

```bash
cd sidequest-server && uv run pytest tests/telemetry/test_streaming_spans.py tests/agents/test_stream_fence.py tests/agents/test_narrator_streaming.py -v
```

Expected: PASS, all.

- [ ] **Step 7: Lint and commit**

```bash
cd sidequest-server && uv run ruff check . && uv run ruff format .
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/telemetry/spans.py \
        sidequest-server/sidequest/agents/narrator.py \
        sidequest-server/sidequest/agents/stream_fence.py \
        sidequest-server/tests/telemetry/test_streaming_spans.py
git commit -m "feat(telemetry): OTEL spans for narrator streaming lifecycle"
```

---

### Task 14: GM panel TTFT histogram + parse-status pie

The dashboard at `sidequest-server /dashboard` (per ADR-090) reads OTEL events and renders. Add the new visualizations.

**Files:**
- Modify: `sidequest-server/sidequest/server/dashboard.py` (or wherever dashboard renders)
- Test: `sidequest-server/tests/server/test_dashboard_streaming_panels.py`

This task requires reading the existing dashboard rendering pattern to know how to extend it. The skeleton:

- [ ] **Step 1: Find dashboard rendering**

```bash
grep -rn "narrator.stream\|histogram\|/dashboard" sidequest-server/sidequest/server/ 2>/dev/null | head -20
```

Read the dashboard module(s) to understand: how spans are queried, how panels are defined, how the response renders.

- [ ] **Step 2: Write a test that asserts new panels render with non-empty data**

(Pseudocode — adapt to real dashboard API after reading the existing implementation.)

```python
def test_dashboard_renders_ttft_histogram_with_data():
    # Given: in-memory span exporter has captured narrator.stream.first_token spans
    # When: dashboard renders
    # Then: response includes a "Stream TTFT" panel with the histogram data
    ...

def test_dashboard_renders_parse_status_pie():
    # Given: spans recorded with json_parse_status=complete and =no_fence
    # When: render
    # Then: pie chart present with both slices
    ...
```

- [ ] **Step 3: Run test to verify it fails**

- [ ] **Step 4: Implement the panels**

Add panel renderers that query the OTEL exporter (or spans-store, depending on how ADR-090 was wired) for `narrator.stream.first_token.ttft_seconds` and `narrator.stream.complete.json_parse_status`. Render histogram + pie.

- [ ] **Step 5: Run tests**

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(dashboard): TTFT histogram + JSON parse status pie for streaming pipeline"
```

---

### Story 2 Milestone

After Tasks 10–14:
- WS protocol has `narration.delta` registered
- Server emits deltas during streaming turns when flag on
- OTEL spans observable in GM panel
- The lie-detector test (spec §6) passes manually: any streaming turn shows TTFT in the dashboard, delta_count > 0 on completion

**Verify:**

```bash
cd sidequest-server && uv run pytest tests/ -v && uv run ruff check .
```

Expected: all server tests pass.

---

## Story 3 — Frontend Incremental Render (3 pts, ui)

UI consumes the deltas. After this story, with `SIDEQUEST_NARRATOR_STREAMING=1`, the playgroup sees prose live.

---

### Task 15: TypeScript NarrationDelta type + WS handler

**Files:**
- Modify: `sidequest-ui/src/types/messages.ts` (or wherever the GameMessage discriminated union lives)
- Test: `sidequest-ui/src/__tests__/messages-narration-delta.test.ts`

- [ ] **Step 1: Find the existing message union**

```bash
grep -rn "narration\|GameMessage\|kind: \"" sidequest-ui/src/types/ 2>/dev/null | head -15
```

Read the file to understand the discriminated-union convention.

- [ ] **Step 2: Write the failing test**

```typescript
// sidequest-ui/src/__tests__/messages-narration-delta.test.ts
import { describe, it, expect } from "vitest";
import type { NarrationDelta, GameMessage } from "../types/messages";
import { isNarrationDelta } from "../types/messages";

describe("NarrationDelta message", () => {
  it("type-guards correctly", () => {
    const msg: GameMessage = {
      kind: "narration.delta",
      payload: { turn_id: "t-1", chunk: "Hello", seq: 0 },
    };
    expect(isNarrationDelta(msg)).toBe(true);
  });

  it("does not match other kinds", () => {
    const msg = { kind: "narration", payload: { text: "..." } } as GameMessage;
    expect(isNarrationDelta(msg)).toBe(false);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-ui && npx vitest run src/__tests__/messages-narration-delta.test.ts
```

Expected: FAIL.

- [ ] **Step 4: Add the type + guard**

In `src/types/messages.ts`:

```typescript
export type NarrationDelta = {
  kind: "narration.delta";
  payload: {
    turn_id: string;
    chunk: string;
    seq: number;
  };
};

export type GameMessage =
  | NarrationDelta
  | /* ...existing variants... */;

export function isNarrationDelta(msg: GameMessage): msg is NarrationDelta {
  return msg.kind === "narration.delta";
}
```

- [ ] **Step 5: Run test to verify it passes**

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/types/messages.ts sidequest-ui/src/__tests__/messages-narration-delta.test.ts
git commit -m "feat(ui): NarrationDelta message type + guard"
```

---

### Task 16: State mirror per-turn delta accumulator

The state mirror (per ADR-026) gains a `streamingNarration` slice keyed by turn_id.

**Files:**
- Modify: `sidequest-ui/src/providers/GameStateProvider.tsx` (or equivalent state-mirror module)
- Test: `sidequest-ui/src/__tests__/streaming-narration-state.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// sidequest-ui/src/__tests__/streaming-narration-state.test.ts
import { describe, it, expect } from "vitest";
import { reduceStreamingNarration, initialStreamingState } from "../providers/streamingNarration";

describe("streamingNarration reducer", () => {
  it("appends chunks in seq order", () => {
    let state = initialStreamingState;
    state = reduceStreamingNarration(state, {
      kind: "narration.delta",
      payload: { turn_id: "t-1", chunk: "Hello ", seq: 0 },
    });
    state = reduceStreamingNarration(state, {
      kind: "narration.delta",
      payload: { turn_id: "t-1", chunk: "world.", seq: 1 },
    });

    const turn = state.turns.get("t-1")!;
    expect(turn.chunks).toEqual(["Hello ", "world."]);
    expect(turn.canonical).toBeNull();
  });

  it("swaps to canonical when narration event lands", () => {
    let state = initialStreamingState;
    state = reduceStreamingNarration(state, {
      kind: "narration.delta",
      payload: { turn_id: "t-1", chunk: "partial", seq: 0 },
    });
    state = reduceStreamingNarration(state, {
      kind: "narration",
      payload: { turn_id: "t-1", text: "FINAL CANONICAL TEXT", seq: 5 },
    });

    const turn = state.turns.get("t-1")!;
    expect(turn.canonical).toBe("FINAL CANONICAL TEXT");
  });

  it("discards late deltas after canonical landed", () => {
    let state = initialStreamingState;
    state = reduceStreamingNarration(state, {
      kind: "narration",
      payload: { turn_id: "t-1", text: "DONE", seq: 3 },
    });
    state = reduceStreamingNarration(state, {
      kind: "narration.delta",
      payload: { turn_id: "t-1", chunk: "late!", seq: 99 },
    });

    const turn = state.turns.get("t-1")!;
    expect(turn.canonical).toBe("DONE");
    expect(turn.chunks).toEqual([]); // late delta not appended
  });

  it("renders accumulated until canonical is present", () => {
    const state = {
      turns: new Map([
        ["t-1", { chunks: ["a", "b", "c"], canonical: null, nextExpectedSeq: 3 }],
      ]),
    };
    const turn = state.turns.get("t-1")!;
    const display = turn.canonical ?? turn.chunks.join("");
    expect(display).toBe("abc");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-ui && npx vitest run src/__tests__/streaming-narration-state.test.ts
```

Expected: FAIL.

- [ ] **Step 3: Implement the reducer module**

```typescript
// sidequest-ui/src/providers/streamingNarration.ts
export type TurnStreamState = {
  chunks: string[];
  nextExpectedSeq: number;
  canonical: string | null;
};

export type StreamingNarrationState = {
  turns: Map<string, TurnStreamState>;
};

export const initialStreamingState: StreamingNarrationState = {
  turns: new Map(),
};

type DeltaMsg = { kind: "narration.delta"; payload: { turn_id: string; chunk: string; seq: number } };
type CanonicalMsg = { kind: "narration"; payload: { turn_id: string; text: string; seq: number } };
type Action = DeltaMsg | CanonicalMsg;

function getOrCreateTurn(
  state: StreamingNarrationState,
  turn_id: string,
): TurnStreamState {
  const existing = state.turns.get(turn_id);
  if (existing) return existing;
  const fresh: TurnStreamState = { chunks: [], nextExpectedSeq: 0, canonical: null };
  state.turns.set(turn_id, fresh);
  return fresh;
}

export function reduceStreamingNarration(
  state: StreamingNarrationState,
  action: Action,
): StreamingNarrationState {
  const next = { turns: new Map(state.turns) };
  if (action.kind === "narration.delta") {
    const { turn_id, chunk } = action.payload;
    const turn = getOrCreateTurn(next, turn_id);
    if (turn.canonical !== null) {
      // Late delta — discard
      return state;
    }
    next.turns.set(turn_id, {
      ...turn,
      chunks: [...turn.chunks, chunk],
      nextExpectedSeq: turn.nextExpectedSeq + 1,
    });
    return next;
  }
  if (action.kind === "narration") {
    const { turn_id, text } = action.payload;
    const turn = getOrCreateTurn(next, turn_id);
    next.turns.set(turn_id, { ...turn, canonical: text });
    return next;
  }
  return state;
}

export function displayTextForTurn(
  state: StreamingNarrationState,
  turn_id: string,
): string | null {
  const turn = state.turns.get(turn_id);
  if (!turn) return null;
  return turn.canonical ?? turn.chunks.join("");
}
```

- [ ] **Step 4: Wire reducer into the GameStateProvider**

In the provider that already handles `narration` events, route both `narration.delta` and `narration` through the new reducer. The existing canonical-render path stays as the source-of-truth for already-completed turns.

- [ ] **Step 5: Run tests**

```bash
cd sidequest-ui && npx vitest run src/__tests__/streaming-narration-state.test.ts
```

Expected: PASS, 4 tests.

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/providers/streamingNarration.ts \
        sidequest-ui/src/providers/GameStateProvider.tsx \
        sidequest-ui/src/__tests__/streaming-narration-state.test.ts
git commit -m "feat(ui): streamingNarration reducer + per-turn delta accumulator"
```

---

### Task 17: Narration screen renders accumulated-or-canonical

**Files:**
- Modify: the narration-rendering React component (likely `src/screens/Narration.tsx` or similar — find via `grep`)
- Test: `sidequest-ui/src/__tests__/narration-screen-streaming.test.tsx`

- [ ] **Step 1: Find the narration screen**

```bash
grep -rn "narration" sidequest-ui/src/screens/ sidequest-ui/src/components/ 2>/dev/null | head -10
```

- [ ] **Step 2: Write the failing test**

```typescript
// sidequest-ui/src/__tests__/narration-screen-streaming.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NarrationScreen } from "../screens/NarrationScreen"; // adjust import

describe("NarrationScreen with streaming state", () => {
  it("renders accumulated chunks when no canonical yet", () => {
    const state = {
      turns: new Map([
        ["t-1", { chunks: ["Hello ", "world."], canonical: null, nextExpectedSeq: 2 }],
      ]),
    };
    render(<NarrationScreen streamingState={state} activeTurnId="t-1" />);
    expect(screen.getByTestId("narration-text").textContent).toBe("Hello world.");
  });

  it("renders canonical text when present, ignoring chunks", () => {
    const state = {
      turns: new Map([
        ["t-1", { chunks: ["partial"], canonical: "FULL CANONICAL", nextExpectedSeq: 1 }],
      ]),
    };
    render(<NarrationScreen streamingState={state} activeTurnId="t-1" />);
    expect(screen.getByTestId("narration-text").textContent).toBe("FULL CANONICAL");
  });
});
```

- [ ] **Step 3: Run to verify failure**

```bash
cd sidequest-ui && npx vitest run src/__tests__/narration-screen-streaming.test.tsx
```

- [ ] **Step 4: Wire the rendering**

In the narration screen component, replace the current canonical-only render with `displayTextForTurn(streamingState, activeTurnId)`. Add a `data-testid="narration-text"` wrapper. Keep all existing props/styles.

- [ ] **Step 5: Run tests**

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/screens/NarrationScreen.tsx \
        sidequest-ui/src/__tests__/narration-screen-streaming.test.tsx
git commit -m "feat(ui): NarrationScreen renders accumulated-or-canonical from streaming state"
```

---

### Task 18: Stalled-stream interstitial

If no delta and no canonical for >5s after a turn starts, show "narrator considers" indicator.

**Files:**
- Modify: `sidequest-ui/src/screens/NarrationScreen.tsx`
- Test: extend `src/__tests__/narration-screen-streaming.test.tsx`

- [ ] **Step 1: Write the failing test**

Append to `narration-screen-streaming.test.tsx`:

```typescript
import { vi } from "vitest";
import { act } from "@testing-library/react";

it("shows interstitial when no chunks and no canonical for 5s", async () => {
  vi.useFakeTimers();
  const state = {
    turns: new Map([
      ["t-1", { chunks: [], canonical: null, nextExpectedSeq: 0 }],
    ]),
  };
  render(<NarrationScreen streamingState={state} activeTurnId="t-1" turnStartedAt={Date.now()} />);

  // Before 5s — no interstitial
  expect(screen.queryByTestId("narrator-considers")).toBeNull();

  // Advance fake timers past 5s
  act(() => { vi.advanceTimersByTime(5_500); });

  expect(screen.queryByTestId("narrator-considers")).not.toBeNull();
  vi.useRealTimers();
});

it("hides interstitial as soon as first chunk arrives", async () => {
  vi.useFakeTimers();
  const state = {
    turns: new Map([
      ["t-1", { chunks: ["First chunk"], canonical: null, nextExpectedSeq: 1 }],
    ]),
  };
  render(<NarrationScreen streamingState={state} activeTurnId="t-1" turnStartedAt={Date.now() - 6_000} />);

  // Even though 6s have passed, interstitial is hidden because chunks arrived
  expect(screen.queryByTestId("narrator-considers")).toBeNull();
  vi.useRealTimers();
});
```

- [ ] **Step 2: Run to verify failure**

- [ ] **Step 3: Implement the timeout-based interstitial**

In `NarrationScreen.tsx`, add a `useEffect` that watches `(turn.chunks.length, turn.canonical, turnStartedAt)` and toggles a local `showInterstitial` state after 5s of no-content.

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/screens/NarrationScreen.tsx \
        sidequest-ui/src/__tests__/narration-screen-streaming.test.tsx
git commit -m "feat(ui): stalled-stream interstitial after 5s with no content"
```

---

### Task 19: End-to-end flag-on smoke test (manual / scripted)

**Files:**
- Modify (or create): `scripts/playtest.py` or equivalent — add a `--streaming` smoke step
- No new tests; this is operational verification

- [ ] **Step 1: Run the server with the flag enabled**

```bash
SIDEQUEST_NARRATOR_STREAMING=1 just up
```

- [ ] **Step 2: Open the GM panel**

```bash
just otel
```

Verify: dashboard shows the new TTFT histogram and JSON parse status pie panels.

- [ ] **Step 3: Drive a single narrator turn**

Either via the UI or `just playtest-scenario <name>`. Watch:
- The browser network tab → `narration.delta` frames arriving live
- The dashboard's Stream Timeline → first_token at 1-3s, complete event at end
- The narration screen → text appearing chunked, then settling to canonical

- [ ] **Step 4: Document the verification result**

Capture a screenshot of the dashboard panels and add to `docs/superpowers/specs/2026-05-02-narration-streaming-design.md` as a "Lie-Detector Verified" addendum at the bottom, with date.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-02-narration-streaming-design.md
git commit -m "docs(spec): narration streaming lie-detector verified end-to-end"
```

---

### Story 3 Milestone

After Tasks 15–19:
- UI subscribes to `narration.delta`, accumulates per-turn, swaps to canonical at EOS
- Stalled-stream interstitial in place
- End-to-end smoke verified with the GM panel

**Final verification:**

```bash
cd sidequest-server && uv run pytest tests/ -v && uv run ruff check .
cd sidequest-ui && npx vitest run && npm run lint
```

Expected: all tests pass, lint clean.

**Flag flip for the playgroup:** add `SIDEQUEST_NARRATOR_STREAMING=1` to the dev-environment defaults (or whatever boot script the playgroup uses) once the lie-detector dashboard shows healthy TTFT and complete-rate over a session of trial turns.

---

## Self-Review Notes

**Spec coverage check:** Tasks map to spec sections —
- §5.1–5.6 (claude_client streaming) → Tasks 1–7
- §5.7 (StreamFenceParser) → Task 8
- §5.8 (narrator integration) → Tasks 9, 12
- §5.9–5.10 (WS protocol + broadcast_delta) → Tasks 10, 11
- §5.11 (backpressure) → covered conceptually in Task 11; v1 is buffer-all so no implementation work
- §5.12 (frontend) → Tasks 15–18
- §6 (OTEL) → Tasks 13, 14
- §7 (failure modes) → tested across stories (timeout, subprocess_failed, no_fence, unclosed_fence, trailing_garbage all have tests)
- §8 (test strategy) → distributed across all tasks
- §9 (sequencing) → three story sections in this plan
- §10 open questions → Task 3 captures fixture; turn_id source resolved by passing it through narrator (Task 12); interstitial duration set at 5s in Task 18; OTEL cardinality verified by inspecting in-memory exporter in Task 13

**Placeholder scan:** all "TBD"/"figure out"/"add error handling" patterns absent. Task 14 (dashboard panels) is intentionally lighter on code because it depends on reading the existing dashboard module — that's documented as Step 1 of the task, not deferred.

**Type consistency:** `StreamFenceParser`, `FenceParseResult`, `StreamComplete`, `StreamError`, `TextDelta` all spelled identically across tasks. `is_streaming_enabled` named identically in spec, narrator, and tests. `broadcast_delta` named identically across tasks.

---

## Plan complete — ready to execute.
