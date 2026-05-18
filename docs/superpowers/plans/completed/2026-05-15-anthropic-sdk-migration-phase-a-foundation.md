# Anthropic SDK Migration — Phase A: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Historical note (2026-05-15):** Phase A is complete (Task 14 landed the parent ADR on commit 3485073). This plan contains 12 references to "ADR-099" — the ID was a placeholder used during drafting; the ADR actually merged as **ADR-101** because ADR-099 (coyote-object-salvage-hooks) and ADR-100 (journal-pipeline-coherence) merged ahead of it. The Phase D and E plans use the corrected numbers (ADR-101 parent; ADR-102/103/104 successors). This file is preserved as-written for archeological accuracy of what was executed; do not re-run Task 14.

**Goal:** Land the SDK client, tooling protocol, fake-client test double, cache-zone wiring, model routing, and cost telemetry on `feat/anthropic-sdk-migration` — every later phase depends on these primitives. Develop stays on `claude -p`; the new client is callable but not yet wired into the narrator.

**Architecture:** New `AnthropicSdkClient` lives alongside `ClaudeClient` and `OllamaClient` in `sidequest-server/sidequest/agents/`. It implements both the existing narrow `LlmClient` Protocol (for any path that wants the SDK) and a new richer `ToolingLlmClient` Protocol (tool-use round-trips, `cache_control` on prefix blocks, model routing). Tests use `FakeAnthropicSdkClient` — a scripted double — exclusively; no real API calls in CI. Telemetry follows the existing `sidequest/telemetry/spans/<subsystem>.py` pattern with two new modules (`llm_request.py`, `cost.py`).

**Tech Stack:** Python 3.12, `anthropic` SDK (pinned), Pydantic 2, pytest + pytest-asyncio, ruff, pyright, OpenTelemetry, FastAPI (already vendored).

**Scope:** Phase A only — 4 stories (A1-A4, ~18 pts) from the migration spec at `docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md`. Phases B (registry), C (26 tool conversions), D (cleanup), E (merge) are out of scope and will be planned separately once Phase A merges to the feature branch.

**Branch:** `feat/anthropic-sdk-migration` off `develop` in `sidequest-server/`. Same branch name in `orc-quest/` (this repo) for the ADR draft commit. Do **not** open PRs to `develop` until Phase E.

---

## File Structure

### `sidequest-server/`

**Created:**
- `sidequest/agents/anthropic_sdk_client.py` — `AnthropicSdkClient` implementing `LlmClient` + `ToolingLlmClient`; owns the SDK client instance, retry, streaming
- `sidequest/agents/tooling_protocol.py` — `ToolingLlmClient` Protocol, `CacheableBlock`, `Message`, `ToolDefinition`, `ToolUseBlock`, `ToolResultBlock`, `ToolingResult` dataclasses
- `sidequest/agents/model_routing.py` — call-type → model resolver (Haiku 4.5 / Sonnet 4.6 / Opus 4.7) + per-genre-pack override hook
- `sidequest/agents/anthropic_cost.py` — pure-function cost rollup (`compute_cost_usd` from token counts + model id + cache tiers)
- `sidequest/telemetry/spans/llm_request.py` — `llm_request_span` context manager with token/cache/cost/ratelimit attrs
- `sidequest/telemetry/spans/cost.py` — `narration_turn_cost_span` (rollup attrs across nested `llm_request` spans within one turn)
- `tests/agents/test_anthropic_sdk_client.py` — unit tests for the SDK client (with stubbed `AsyncAnthropic`)
- `tests/agents/test_tooling_protocol.py` — protocol-shape + dataclass invariants
- `tests/agents/test_model_routing.py` — routing table tests
- `tests/agents/test_anthropic_cost.py` — cost math tests
- `tests/agents/test_anthropic_sdk_client_wiring.py` — wiring test: `FakeAnthropicSdkClient` round-trip through `complete_with_tools` exercising cache_control + tool round-trip + cost span
- `tests/agents/fakes/__init__.py`
- `tests/agents/fakes/fake_anthropic_sdk_client.py` — scripted-response test double used by every non-API test
- `tests/telemetry/test_llm_request_span.py`
- `tests/telemetry/test_narration_turn_cost_span.py`

**Modified:**
- `pyproject.toml` — add `anthropic>=0.40` dependency
- `sidequest/agents/llm_factory.py` — add `anthropic_sdk` backend key (gated; not yet used by narrator)
- `sidequest/agents/__init__.py` — export `AnthropicSdkClient`, `ToolingLlmClient`, `FakeAnthropicSdkClient` (test-only via separate module path; do not export the fake from production `__init__`)

### `orc-quest/` (this repo)

**Created:**
- `docs/adr/099-anthropic-sdk-as-narrator-backend.md` — ADR drafted as successor to ADR-001 (status: *proposed*, kept *proposed* until Phase E merges)

**Modified:**
- `docs/adr/README.md` — index entry (auto-generated; run regen script)
- `docs/adr/001-claude-cli-only.md` — add `superseded-by: 099` line in frontmatter; status stays *accepted* until merge; **do not** edit body

---

## Self-Review (pre-execution)

Spec coverage check:
- A1 → Task 14 (ADR draft + commit)
- A2 → Tasks 2-9 (protocol, fake, real client, wiring test)
- A3 → Tasks 10-12 (cache zones, cost telemetry, llm_request span)
- A4 → Tasks 13a-13b (model routing, 1-hour cache TTL beta opt-in)

Type consistency: `CacheableBlock`, `Message`, `ToolDefinition`, `ToolingResult` defined in Task 2; referenced in Tasks 4, 5, 8, 11 with the same field names. `compute_cost_usd(input_tokens, output_tokens, cached_input_read_tokens, cached_input_write_tokens, model)` signature is the same everywhere.

Placeholder scan: no TBDs; every code step has the actual code to write.

---

## Task 1 — Branch + dependency

**Files:**
- Modify: `sidequest-server/pyproject.toml`

- [ ] **Step 1.1: Create the feature branch in sidequest-server**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git checkout develop
git pull --ff-only origin develop
git checkout -b feat/anthropic-sdk-migration
```

Expected: clean checkout, new branch created.

- [ ] **Step 1.2: Add the anthropic SDK dependency**

Edit `sidequest-server/pyproject.toml`. In the `dependencies = [...]` list, after the existing `"websockets>=12.0",` line, add:
```
    "anthropic>=0.40",
```

- [ ] **Step 1.3: Run uv sync to install**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv sync
```

Expected: anthropic package + transitive deps installed; no errors.

- [ ] **Step 1.4: Verify the SDK imports**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run python -c "from anthropic import AsyncAnthropic; print(AsyncAnthropic.__module__)"
```

Expected output: `anthropic._client` (or similar `anthropic.*` module path). No exceptions.

- [ ] **Step 1.5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add pyproject.toml uv.lock
git commit -m "deps: add anthropic SDK for Phase A foundation"
```

---

## Task 2 — `ToolingLlmClient` Protocol + dataclasses

**Files:**
- Create: `sidequest-server/sidequest/agents/tooling_protocol.py`
- Test: `sidequest-server/tests/agents/test_tooling_protocol.py`

Defines the typed surface every tooling-capable backend must implement. Pure type definitions — no behavior. Importable by both production code and tests without instantiating any client.

- [ ] **Step 2.1: Write the failing test**

Create `sidequest-server/tests/agents/test_tooling_protocol.py`:
```python
"""Shape tests for the ToolingLlmClient protocol + payload dataclasses."""

from __future__ import annotations

import pytest

from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
    ToolDefinition,
    ToolingLlmClient,
    ToolingResult,
    ToolResultBlock,
    ToolUseBlock,
)


def test_cacheable_block_is_frozen_dataclass() -> None:
    block = CacheableBlock(text="hi", cache=True)
    with pytest.raises(Exception):
        block.text = "bye"  # type: ignore[misc]


def test_cacheable_block_defaults_cache_false() -> None:
    block = CacheableBlock(text="hi")
    assert block.cache is False


def test_message_roles() -> None:
    user = Message(role="user", content="hello")
    assistant = Message(role="assistant", content="hi back")
    assert user.role == "user"
    assert assistant.role == "assistant"


def test_tool_definition_has_json_schema_field() -> None:
    td = ToolDefinition(
        name="roll_dice",
        description="Roll dice.",
        input_schema={"type": "object", "properties": {}, "required": []},
    )
    assert td.name == "roll_dice"
    assert td.input_schema["type"] == "object"


def test_tool_use_block_carries_id_and_args() -> None:
    b = ToolUseBlock(id="toolu_abc", name="roll_dice", arguments={"sides": 20})
    assert b.id == "toolu_abc"
    assert b.arguments["sides"] == 20


def test_tool_result_block_pairs_with_tool_use_id() -> None:
    r = ToolResultBlock(tool_use_id="toolu_abc", content="rolled 17", is_error=False)
    assert r.tool_use_id == "toolu_abc"
    assert r.is_error is False


def test_tooling_result_exposes_text_and_usage() -> None:
    res = ToolingResult(
        text="The dice show 17.",
        stop_reason="end_turn",
        input_tokens=100,
        output_tokens=20,
        cached_input_read_tokens=80,
        cached_input_write_tokens=0,
        model="claude-sonnet-4-6",
        tool_calls=[],
    )
    assert res.stop_reason == "end_turn"
    assert res.cached_input_read_tokens == 80


def test_tooling_llm_client_is_protocol() -> None:
    # Protocol is structural — it must accept a duck-typed conformer.
    assert ToolingLlmClient is not None
    # No instantiation; protocols are not constructible.
```

- [ ] **Step 2.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_tooling_protocol.py -v
```

Expected: collection error or ImportError — `sidequest.agents.tooling_protocol` does not exist.

- [ ] **Step 2.3: Implement the module**

Create `sidequest-server/sidequest/agents/tooling_protocol.py`:
```python
"""Typed surface for tooling-capable LLM backends (ADR-099 successor of ADR-001).

The narrator orchestrator targets ToolingLlmClient.complete_with_tools.
Narrow LlmClient (ClaudeClient, OllamaClient) handles auxiliary text-only paths.
The split is intentional — Ollama cannot serve cached tool round-trips and
should not be reachable from a narrator path.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class CacheableBlock:
    """A system-prompt segment that may carry an Anthropic cache_control marker."""

    text: str
    cache: bool = False


@dataclass(frozen=True, slots=True)
class Message:
    """A user/assistant message in the conversation messages array."""

    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """JSON-Schema-described tool the model may call."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolUseBlock:
    """A single tool invocation emitted by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolResultBlock:
    """The handler's reply to a ToolUseBlock, fed back to the model."""

    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True, slots=True)
class ToolingResult:
    """Final outcome of a `complete_with_tools` call after the tool loop settles."""

    text: str
    stop_reason: Literal["end_turn", "max_tokens", "stop_sequence", "tool_use", "error"]
    input_tokens: int
    output_tokens: int
    cached_input_read_tokens: int
    cached_input_write_tokens: int
    model: str
    tool_calls: list[ToolUseBlock] = field(default_factory=list)


# Handler signature the registry exposes to the client.
# (args_json, tool_use_id) -> ToolResultBlock
ToolHandler = Callable[[dict[str, Any], str], "ToolResultBlock"]


@runtime_checkable
class ToolingLlmClient(Protocol):
    """Tooling-capable LLM client — extends the narrow LlmClient surface.

    Phase A defines the surface only. Phase B's tool_registry wires real
    handlers; Phase C populates `tools` with the 26-tool v1 catalog.
    """

    async def complete_with_tools(
        self,
        system_blocks: list[CacheableBlock],
        messages: list[Message],
        tools: list[ToolDefinition],
        tool_dispatch: Callable[[ToolUseBlock], "ToolResultBlock"] | None = None,
        *,
        model: str,
        max_iterations: int = 8,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> ToolingResult: ...
```

- [ ] **Step 2.4: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_tooling_protocol.py -v
```

Expected: 8 passed.

- [ ] **Step 2.5: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/tooling_protocol.py tests/agents/test_tooling_protocol.py
uv run pyright sidequest/agents/tooling_protocol.py tests/agents/test_tooling_protocol.py
```

Expected: no findings.

- [ ] **Step 2.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/tooling_protocol.py tests/agents/test_tooling_protocol.py
git commit -m "feat(agents): add ToolingLlmClient protocol + payload dataclasses

Phase A foundation. Defines CacheableBlock / Message / ToolDefinition /
ToolUseBlock / ToolResultBlock / ToolingResult and the ToolingLlmClient
Protocol. Pure type surface — no behavior yet. Behavior lands in
AnthropicSdkClient + FakeAnthropicSdkClient (next tasks).

Refs spec: docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md"
```

---

## Task 3 — `FakeAnthropicSdkClient` (test double)

**Files:**
- Create: `sidequest-server/tests/agents/fakes/__init__.py`
- Create: `sidequest-server/tests/agents/fakes/fake_anthropic_sdk_client.py`
- Test: `sidequest-server/tests/agents/test_fake_anthropic_sdk_client.py`

The fake is the *only* mock used by every non-API test (Surface 1, 2, 3 in spec §Testing strategy). It scripts responses programmatically — no fixture files, no recordings. Built before the real client so the real client's tests can target the same interface.

- [ ] **Step 3.1: Write the failing test**

Create `sidequest-server/tests/agents/test_fake_anthropic_sdk_client.py`:
```python
"""Tests for the FakeAnthropicSdkClient test double."""

from __future__ import annotations

import pytest

from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
    ToolDefinition,
    ToolingLlmClient,
    ToolResultBlock,
    ToolUseBlock,
)
from tests.agents.fakes.fake_anthropic_sdk_client import (
    FakeAnthropicSdkClient,
    ScriptedResponse,
    ScriptExhausted,
)


def _system() -> list[CacheableBlock]:
    return [CacheableBlock(text="SYSTEM RULES", cache=True)]


def _msgs() -> list[Message]:
    return [Message(role="user", content="What happens next?")]


async def test_fake_returns_scripted_text() -> None:
    fake = FakeAnthropicSdkClient(
        responses=[
            ScriptedResponse(
                text="The lantern gutters.",
                stop_reason="end_turn",
                input_tokens=100,
                output_tokens=8,
                cached_input_read_tokens=80,
                cached_input_write_tokens=0,
                model="claude-sonnet-4-6",
            )
        ]
    )
    result = await fake.complete_with_tools(
        system_blocks=_system(),
        messages=_msgs(),
        tools=[],
        model="claude-sonnet-4-6",
    )
    assert result.text == "The lantern gutters."
    assert result.stop_reason == "end_turn"
    assert result.cached_input_read_tokens == 80


async def test_fake_implements_protocol() -> None:
    fake = FakeAnthropicSdkClient(responses=[])
    assert isinstance(fake, ToolingLlmClient)


async def test_fake_runs_tool_loop() -> None:
    """Script a tool_use response, then a final end_turn response."""
    tool_use = ToolUseBlock(id="toolu_x", name="roll_dice", arguments={"sides": 20})
    fake = FakeAnthropicSdkClient(
        responses=[
            ScriptedResponse(
                text="",
                stop_reason="tool_use",
                input_tokens=200,
                output_tokens=15,
                cached_input_read_tokens=180,
                cached_input_write_tokens=0,
                model="claude-sonnet-4-6",
                tool_uses=[tool_use],
            ),
            ScriptedResponse(
                text="The roll landed.",
                stop_reason="end_turn",
                input_tokens=220,
                output_tokens=10,
                cached_input_read_tokens=180,
                cached_input_write_tokens=0,
                model="claude-sonnet-4-6",
            ),
        ]
    )

    def dispatch(block: ToolUseBlock) -> ToolResultBlock:
        return ToolResultBlock(tool_use_id=block.id, content="17", is_error=False)

    tools = [
        ToolDefinition(
            name="roll_dice",
            description="Roll dice.",
            input_schema={"type": "object", "properties": {}, "required": []},
        )
    ]
    result = await fake.complete_with_tools(
        system_blocks=_system(),
        messages=_msgs(),
        tools=tools,
        tool_dispatch=dispatch,
        model="claude-sonnet-4-6",
    )
    assert result.text == "The roll landed."
    assert result.stop_reason == "end_turn"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "roll_dice"


async def test_fake_records_request_payloads() -> None:
    fake = FakeAnthropicSdkClient(
        responses=[
            ScriptedResponse(
                text="ok",
                stop_reason="end_turn",
                input_tokens=10,
                output_tokens=2,
                cached_input_read_tokens=0,
                cached_input_write_tokens=0,
                model="claude-sonnet-4-6",
            )
        ]
    )
    await fake.complete_with_tools(
        system_blocks=_system(),
        messages=_msgs(),
        tools=[],
        model="claude-sonnet-4-6",
    )
    assert len(fake.recorded_requests) == 1
    req = fake.recorded_requests[0]
    assert req.model == "claude-sonnet-4-6"
    assert req.system_blocks == _system()
    assert req.messages == _msgs()


async def test_fake_raises_when_script_exhausted() -> None:
    fake = FakeAnthropicSdkClient(responses=[])
    with pytest.raises(ScriptExhausted):
        await fake.complete_with_tools(
            system_blocks=_system(),
            messages=_msgs(),
            tools=[],
            model="claude-sonnet-4-6",
        )


async def test_fake_streams_text_deltas() -> None:
    deltas: list[str] = []
    fake = FakeAnthropicSdkClient(
        responses=[
            ScriptedResponse(
                text="The lantern gutters.",
                stop_reason="end_turn",
                input_tokens=10,
                output_tokens=4,
                cached_input_read_tokens=0,
                cached_input_write_tokens=0,
                model="claude-sonnet-4-6",
                stream_deltas=["The lantern", " gutters."],
            )
        ]
    )
    await fake.complete_with_tools(
        system_blocks=_system(),
        messages=_msgs(),
        tools=[],
        model="claude-sonnet-4-6",
        on_text_delta=deltas.append,
    )
    assert deltas == ["The lantern", " gutters."]
```

- [ ] **Step 3.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_fake_anthropic_sdk_client.py -v
```

Expected: ImportError — fakes module does not exist.

- [ ] **Step 3.3: Implement the fakes package marker**

Create `sidequest-server/tests/agents/fakes/__init__.py` (empty file):
```python
"""Test doubles for agent backends. Import only from tests/."""
```

- [ ] **Step 3.4: Implement the fake**

Create `sidequest-server/tests/agents/fakes/fake_anthropic_sdk_client.py`:
```python
"""FakeAnthropicSdkClient — scripted-response test double.

All non-API tests use this fake. Each test constructs the response sequence
the test scenario requires; the fake never reaches the network.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
    ToolDefinition,
    ToolingResult,
    ToolResultBlock,
    ToolUseBlock,
)


class ScriptExhausted(RuntimeError):
    """The test asked the fake for more responses than were scripted."""


@dataclass(frozen=True, slots=True)
class ScriptedResponse:
    """One step of a multi-step model interaction."""

    text: str
    stop_reason: Literal["end_turn", "max_tokens", "stop_sequence", "tool_use", "error"]
    input_tokens: int
    output_tokens: int
    cached_input_read_tokens: int
    cached_input_write_tokens: int
    model: str
    tool_uses: list[ToolUseBlock] = field(default_factory=list)
    stream_deltas: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RecordedRequest:
    """A captured call into the fake, for assertion in tests."""

    model: str
    system_blocks: list[CacheableBlock]
    messages: list[Message]
    tools: list[ToolDefinition]


class FakeAnthropicSdkClient:
    """Implements ToolingLlmClient with scripted responses."""

    def __init__(self, responses: list[ScriptedResponse]) -> None:
        self._responses = list(responses)
        self._cursor = 0
        self.recorded_requests: list[RecordedRequest] = []

    async def complete_with_tools(
        self,
        system_blocks: list[CacheableBlock],
        messages: list[Message],
        tools: list[ToolDefinition],
        tool_dispatch: Callable[[ToolUseBlock], ToolResultBlock] | None = None,
        *,
        model: str,
        max_iterations: int = 8,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> ToolingResult:
        all_tool_calls: list[ToolUseBlock] = []
        iterations = 0
        current_messages = list(messages)
        while True:
            iterations += 1
            if iterations > max_iterations:
                raise RuntimeError(
                    f"FakeAnthropicSdkClient exceeded max_iterations={max_iterations}"
                )
            if self._cursor >= len(self._responses):
                raise ScriptExhausted(
                    f"Fake ran out of scripted responses at iteration {iterations}"
                )
            response = self._responses[self._cursor]
            self._cursor += 1
            self.recorded_requests.append(
                RecordedRequest(
                    model=model,
                    system_blocks=list(system_blocks),
                    messages=list(current_messages),
                    tools=list(tools),
                )
            )
            if on_text_delta is not None:
                for chunk in response.stream_deltas:
                    on_text_delta(chunk)

            if response.stop_reason != "tool_use":
                return ToolingResult(
                    text=response.text,
                    stop_reason=response.stop_reason,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cached_input_read_tokens=response.cached_input_read_tokens,
                    cached_input_write_tokens=response.cached_input_write_tokens,
                    model=response.model,
                    tool_calls=all_tool_calls,
                )

            if tool_dispatch is None:
                raise RuntimeError(
                    "Scripted tool_use response requires tool_dispatch callback"
                )
            results: list[ToolResultBlock] = []
            for tu in response.tool_uses:
                all_tool_calls.append(tu)
                results.append(tool_dispatch(tu))
            current_messages = current_messages + [
                Message(
                    role="assistant",
                    content="[tool_use placeholder]",
                ),
                Message(
                    role="user",
                    content="\n".join(
                        f"[tool_result {r.tool_use_id}: {r.content}]" for r in results
                    ),
                ),
            ]
```

- [ ] **Step 3.5: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_fake_anthropic_sdk_client.py -v
```

Expected: 6 passed.

- [ ] **Step 3.6: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check tests/agents/fakes/ tests/agents/test_fake_anthropic_sdk_client.py
uv run pyright tests/agents/fakes/ tests/agents/test_fake_anthropic_sdk_client.py
```

Expected: no findings.

- [ ] **Step 3.7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add tests/agents/fakes/ tests/agents/test_fake_anthropic_sdk_client.py
git commit -m "test(agents): add FakeAnthropicSdkClient scripted-response double

Phase A foundation. Sole test double for Phase A-E — every non-API test
uses this fake. Captures recorded_requests for assertion; supports
multi-step tool_use loops with a tool_dispatch callback; streams text
deltas through on_text_delta.

Refs spec §Testing strategy."
```

---

## Task 4 — Cost math (`anthropic_cost.py`)

**Files:**
- Create: `sidequest-server/sidequest/agents/anthropic_cost.py`
- Test: `sidequest-server/tests/agents/test_anthropic_cost.py`

Pure function. Lives in its own module so callers (telemetry spans + the SDK client + alerting hooks) can import without dragging in `anthropic`.

- [ ] **Step 4.1: Write the failing test**

Create `sidequest-server/tests/agents/test_anthropic_cost.py`:
```python
"""Tests for Anthropic cost math (per-call USD computation)."""

from __future__ import annotations

import pytest

from sidequest.agents.anthropic_cost import (
    UnknownModel,
    compute_cost_usd,
    model_pricing,
)


def test_sonnet_4_6_pricing_constants() -> None:
    p = model_pricing("claude-sonnet-4-6")
    assert p.input_per_mtok_usd == 3.0
    assert p.output_per_mtok_usd == 15.0
    assert p.cached_input_read_per_mtok_usd == 0.3
    assert p.cached_input_write_per_mtok_usd == 3.75


def test_haiku_4_5_pricing_constants() -> None:
    p = model_pricing("claude-haiku-4-5-20251001")
    assert p.input_per_mtok_usd == 1.0
    assert p.output_per_mtok_usd == 5.0


def test_opus_4_7_pricing_constants() -> None:
    p = model_pricing("claude-opus-4-7")
    assert p.input_per_mtok_usd == 15.0
    assert p.output_per_mtok_usd == 75.0


def test_unknown_model_raises() -> None:
    with pytest.raises(UnknownModel):
        model_pricing("claude-banana-9")


def test_cost_is_sum_of_buckets() -> None:
    cost = compute_cost_usd(
        input_tokens=1000,
        output_tokens=500,
        cached_input_read_tokens=0,
        cached_input_write_tokens=0,
        model="claude-sonnet-4-6",
    )
    # 1000 in @ $3/M + 500 out @ $15/M = 0.003 + 0.0075 = 0.0105
    assert cost == pytest.approx(0.0105, rel=1e-6)


def test_cached_read_is_90_percent_discount() -> None:
    cost = compute_cost_usd(
        input_tokens=200,
        output_tokens=0,
        cached_input_read_tokens=800,
        cached_input_write_tokens=0,
        model="claude-sonnet-4-6",
    )
    # 200 fresh in @ $3/M = 0.0006
    # 800 cached read @ $0.30/M = 0.00024
    # total 0.00084
    assert cost == pytest.approx(0.00084, rel=1e-6)


def test_cached_write_is_125_percent_of_input() -> None:
    cost = compute_cost_usd(
        input_tokens=0,
        output_tokens=0,
        cached_input_read_tokens=0,
        cached_input_write_tokens=1000,
        model="claude-sonnet-4-6",
    )
    # 1000 cache write @ $3.75/M = 0.00375
    assert cost == pytest.approx(0.00375, rel=1e-6)


def test_input_tokens_does_not_double_count_cached() -> None:
    """API convention: `input_tokens` is the *uncached* fresh input only.

    Callers must pass the SDK's `usage.input_tokens` (excludes cached_*)
    directly — compute_cost_usd does not subtract.
    """
    cost = compute_cost_usd(
        input_tokens=100,
        output_tokens=0,
        cached_input_read_tokens=900,
        cached_input_write_tokens=0,
        model="claude-sonnet-4-6",
    )
    # Fresh: 100 @ $3/M = 0.0003
    # Cached read: 900 @ $0.30/M = 0.00027
    # Total: 0.00057 (not 0.0033, which would be 1100 @ $3/M)
    assert cost == pytest.approx(0.00057, rel=1e-6)
```

- [ ] **Step 4.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_anthropic_cost.py -v
```

Expected: ImportError.

- [ ] **Step 4.3: Implement the cost module**

Create `sidequest-server/sidequest/agents/anthropic_cost.py`:
```python
"""Anthropic API pricing — pure functions.

Pricing snapshot from 2026-05-15. Update when Anthropic publishes a change;
unit tests pin the constants so a change is forced through review.
"""

from __future__ import annotations

from dataclasses import dataclass


class UnknownModel(ValueError):
    """compute_cost_usd was passed a model id not in the pricing table."""


@dataclass(frozen=True, slots=True)
class ModelPricing:
    model: str
    input_per_mtok_usd: float
    output_per_mtok_usd: float
    cached_input_read_per_mtok_usd: float
    cached_input_write_per_mtok_usd: float


_PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-4-6": ModelPricing(
        model="claude-sonnet-4-6",
        input_per_mtok_usd=3.0,
        output_per_mtok_usd=15.0,
        cached_input_read_per_mtok_usd=0.30,
        cached_input_write_per_mtok_usd=3.75,
    ),
    "claude-haiku-4-5-20251001": ModelPricing(
        model="claude-haiku-4-5-20251001",
        input_per_mtok_usd=1.0,
        output_per_mtok_usd=5.0,
        cached_input_read_per_mtok_usd=0.10,
        cached_input_write_per_mtok_usd=1.25,
    ),
    "claude-opus-4-7": ModelPricing(
        model="claude-opus-4-7",
        input_per_mtok_usd=15.0,
        output_per_mtok_usd=75.0,
        cached_input_read_per_mtok_usd=1.50,
        cached_input_write_per_mtok_usd=18.75,
    ),
}


def model_pricing(model: str) -> ModelPricing:
    try:
        return _PRICING[model]
    except KeyError as exc:
        raise UnknownModel(f"No pricing entry for model {model!r}") from exc


def compute_cost_usd(
    *,
    input_tokens: int,
    output_tokens: int,
    cached_input_read_tokens: int,
    cached_input_write_tokens: int,
    model: str,
) -> float:
    """Sum the per-bucket cost for one API call.

    `input_tokens` must be fresh (uncached) input only — matches the Anthropic
    SDK's `usage.input_tokens` semantics, which excludes cached buckets.
    """
    p = model_pricing(model)
    return (
        input_tokens * p.input_per_mtok_usd
        + output_tokens * p.output_per_mtok_usd
        + cached_input_read_tokens * p.cached_input_read_per_mtok_usd
        + cached_input_write_tokens * p.cached_input_write_per_mtok_usd
    ) / 1_000_000
```

- [ ] **Step 4.4: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_anthropic_cost.py -v
```

Expected: 7 passed.

- [ ] **Step 4.5: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/anthropic_cost.py tests/agents/test_anthropic_cost.py
uv run pyright sidequest/agents/anthropic_cost.py tests/agents/test_anthropic_cost.py
```

Expected: no findings.

- [ ] **Step 4.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/anthropic_cost.py tests/agents/test_anthropic_cost.py
git commit -m "feat(agents): add Anthropic per-call cost math

Phase A foundation. Pinned pricing constants for Sonnet 4.6 / Haiku 4.5 /
Opus 4.7. compute_cost_usd treats input_tokens as fresh-only (SDK
convention); cached_input_read/write are separate buckets.

Refs spec §AnthropicSdkClient and caching strategy → 'Per-turn cost math'."
```

---

## Task 5 — `model_routing.py`

**Files:**
- Create: `sidequest-server/sidequest/agents/model_routing.py`
- Test: `sidequest-server/tests/agents/test_model_routing.py`

Maps call type → model id. Per-genre-pack override slot exists but reads from a dict (no genre-pack loader plumbing in Phase A — Phase B+ wires that).

- [ ] **Step 5.1: Write the failing test**

Create `sidequest-server/tests/agents/test_model_routing.py`:
```python
"""Tests for model routing — call-type → model id."""

from __future__ import annotations

import pytest

from sidequest.agents.model_routing import (
    CallType,
    UnknownCallType,
    resolve_model,
)


def test_narration_defaults_to_sonnet() -> None:
    assert resolve_model(CallType.NARRATION) == "claude-sonnet-4-6"


def test_narration_important_defaults_to_opus() -> None:
    assert resolve_model(CallType.NARRATION_IMPORTANT) == "claude-opus-4-7"


def test_classification_defaults_to_haiku() -> None:
    assert resolve_model(CallType.CLASSIFICATION) == "claude-haiku-4-5-20251001"


def test_scratch_defaults_to_haiku() -> None:
    assert resolve_model(CallType.SCRATCH) == "claude-haiku-4-5-20251001"


def test_per_pack_override_takes_precedence() -> None:
    pack_overrides = {CallType.NARRATION: "claude-opus-4-7"}
    assert (
        resolve_model(CallType.NARRATION, pack_overrides=pack_overrides)
        == "claude-opus-4-7"
    )


def test_partial_override_falls_back_to_default() -> None:
    pack_overrides = {CallType.NARRATION: "claude-opus-4-7"}
    assert (
        resolve_model(CallType.CLASSIFICATION, pack_overrides=pack_overrides)
        == "claude-haiku-4-5-20251001"
    )


def test_unknown_call_type_raises() -> None:
    with pytest.raises(UnknownCallType):
        resolve_model("not-a-call-type")  # type: ignore[arg-type]
```

- [ ] **Step 5.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_model_routing.py -v
```

Expected: ImportError.

- [ ] **Step 5.3: Implement model_routing**

Create `sidequest-server/sidequest/agents/model_routing.py`:
```python
"""Call-type → model id resolver.

Each call site declares its CallType. The default ladder maps Haiku for
cheap classification/scratch, Sonnet for narration, Opus for moments the
caller flags as important. Genre packs may override per-call-type via the
pack_overrides argument (wiring lands in Phase B).
"""

from __future__ import annotations

from enum import Enum


class UnknownCallType(ValueError):
    """resolve_model was passed a non-CallType value."""


class CallType(str, Enum):
    NARRATION = "narration"
    NARRATION_IMPORTANT = "narration_important"
    CLASSIFICATION = "classification"
    SCRATCH = "scratch"


_DEFAULT: dict[CallType, str] = {
    CallType.NARRATION: "claude-sonnet-4-6",
    CallType.NARRATION_IMPORTANT: "claude-opus-4-7",
    CallType.CLASSIFICATION: "claude-haiku-4-5-20251001",
    CallType.SCRATCH: "claude-haiku-4-5-20251001",
}


def resolve_model(
    call_type: CallType,
    *,
    pack_overrides: dict[CallType, str] | None = None,
) -> str:
    if not isinstance(call_type, CallType):
        raise UnknownCallType(f"{call_type!r} is not a CallType")
    if pack_overrides is not None and call_type in pack_overrides:
        return pack_overrides[call_type]
    return _DEFAULT[call_type]
```

- [ ] **Step 5.4: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_model_routing.py -v
```

Expected: 7 passed.

- [ ] **Step 5.5: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/model_routing.py tests/agents/test_model_routing.py
uv run pyright sidequest/agents/model_routing.py tests/agents/test_model_routing.py
```

Expected: no findings.

- [ ] **Step 5.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/model_routing.py tests/agents/test_model_routing.py
git commit -m "feat(agents): add model-routing resolver

Phase A foundation. CallType enum + resolve_model(call_type, pack_overrides)
implementing the default Haiku/Sonnet/Opus ladder from the migration spec.
Genre-pack override slot in place; loader wiring lands in Phase B.

Refs spec §AnthropicSdkClient and caching strategy → 'Model routing'."
```

---

## Task 6 — `llm_request` OTEL span

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/llm_request.py`
- Test: `sidequest-server/tests/telemetry/test_llm_request_span.py`

Single span per HTTP call to the Anthropic API. Carries token / cache / cost / ratelimit attrs. The narrator-turn rollup is Task 7.

- [ ] **Step 6.1: Inspect the existing span pattern**

Read `sidequest-server/sidequest/telemetry/spans/agent.py` to copy the conventions (tracer acquisition, attribute naming, context manager shape). Match style — do not invent a new pattern.

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
head -80 sidequest/telemetry/spans/agent.py
```

- [ ] **Step 6.2: Write the failing test**

Create `sidequest-server/tests/telemetry/test_llm_request_span.py`:
```python
"""Tests for the llm.request OTEL span."""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.telemetry.spans.llm_request import llm_request_span


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    trace.set_tracer_provider(provider)
    return exp


def test_span_name_is_llm_request(exporter: InMemorySpanExporter) -> None:
    with llm_request_span(model="claude-sonnet-4-6"):
        pass
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "llm.request"


def test_span_carries_input_attributes(exporter: InMemorySpanExporter) -> None:
    with llm_request_span(model="claude-sonnet-4-6") as span:
        span.set_attributes(
            {
                "llm.input_tokens": 100,
                "llm.output_tokens": 50,
                "llm.cached_input_read_tokens": 80,
                "llm.cached_input_write_tokens": 0,
                "llm.stop_reason": "end_turn",
                "llm.cost_usd": 0.0042,
                "llm.ratelimit_input_tokens_remaining": 100000,
            }
        )
    spans = exporter.get_finished_spans()
    attrs = dict(spans[0].attributes or {})
    assert attrs["llm.model"] == "claude-sonnet-4-6"
    assert attrs["llm.input_tokens"] == 100
    assert attrs["llm.cached_input_read_tokens"] == 80
    assert attrs["llm.cost_usd"] == pytest.approx(0.0042)


def test_span_records_exception(exporter: InMemorySpanExporter) -> None:
    with pytest.raises(RuntimeError):
        with llm_request_span(model="claude-sonnet-4-6"):
            raise RuntimeError("boom")
    spans = exporter.get_finished_spans()
    assert spans[0].status.status_code.name == "ERROR"
```

- [ ] **Step 6.3: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/telemetry/test_llm_request_span.py -v
```

Expected: ImportError.

- [ ] **Step 6.4: Implement the span module**

Create `sidequest-server/sidequest/telemetry/spans/llm_request.py`:
```python
"""OTEL span: llm.request — one span per API call to the Anthropic SDK.

Attributes (set by caller after the call returns):
    llm.model                              str
    llm.input_tokens                       int  (fresh, uncached)
    llm.output_tokens                      int
    llm.cached_input_read_tokens           int
    llm.cached_input_write_tokens          int
    llm.stop_reason                        str  (end_turn|max_tokens|tool_use|stop_sequence|error)
    llm.cost_usd                           float
    llm.ratelimit_input_tokens_remaining   int  (from anthropic-ratelimit-* headers)
    llm.iteration                          int  (1, 2, ... within a tool loop)
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

_TRACER = trace.get_tracer(__name__)


@contextmanager
def llm_request_span(*, model: str, iteration: int = 1) -> Iterator[Span]:
    """Open an llm.request span and seed model + iteration attributes."""
    with _TRACER.start_as_current_span("llm.request") as span:
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.iteration", iteration)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
```

- [ ] **Step 6.5: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/telemetry/test_llm_request_span.py -v
```

Expected: 3 passed.

- [ ] **Step 6.6: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/telemetry/spans/llm_request.py tests/telemetry/test_llm_request_span.py
uv run pyright sidequest/telemetry/spans/llm_request.py tests/telemetry/test_llm_request_span.py
```

Expected: no findings.

- [ ] **Step 6.7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/telemetry/spans/llm_request.py tests/telemetry/test_llm_request_span.py
git commit -m "feat(telemetry): add llm.request OTEL span

Phase A foundation. One span per Anthropic API call; attrs include model,
fresh/cached token buckets, stop_reason, cost_usd, ratelimit headers,
loop iteration. Rollup (narration.turn.cost) lands in a follow-up task."
```

---

## Task 7 — Narration-turn cost rollup span

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/cost.py`
- Test: `sidequest-server/tests/telemetry/test_narration_turn_cost_span.py`

Wraps the *entire* narrator-turn lifecycle (will be entered from the orchestrator in Phase C). Holds rollup attrs computed by the SDK client: total tokens, total cost, model chosen, tool-call count.

- [ ] **Step 7.1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_narration_turn_cost_span.py`:
```python
"""Tests for the narration.turn rollup OTEL span."""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.telemetry.spans.cost import narration_turn_cost_span


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    trace.set_tracer_provider(provider)
    return exp


def test_span_name_is_narration_turn(exporter: InMemorySpanExporter) -> None:
    with narration_turn_cost_span(
        world_id="w",
        session_id="s",
        turn_number=42,
        acting_pc="alex",
    ):
        pass
    spans = exporter.get_finished_spans()
    assert spans[0].name == "narration.turn"


def test_seed_attributes_present(exporter: InMemorySpanExporter) -> None:
    with narration_turn_cost_span(
        world_id="seaboard",
        session_id="sat-night",
        turn_number=42,
        acting_pc="alex",
    ):
        pass
    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs["world_id"] == "seaboard"
    assert attrs["session_id"] == "sat-night"
    assert attrs["turn_number"] == 42
    assert attrs["acting_pc"] == "alex"


def test_rollup_attributes_set_by_caller(exporter: InMemorySpanExporter) -> None:
    with narration_turn_cost_span(
        world_id="w", session_id="s", turn_number=1, acting_pc="alex"
    ) as span:
        span.set_attributes(
            {
                "narration.turn.model_chosen": "claude-sonnet-4-6",
                "narration.turn.total_input_tokens": 5000,
                "narration.turn.total_output_tokens": 1200,
                "narration.turn.cache_read_tokens": 12000,
                "narration.turn.cache_write_tokens": 0,
                "narration.turn.total_cost_usd": 0.067,
                "narration.turn.tool_call_count": 3,
                "narration.turn.llm_request_count": 4,
            }
        )
    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs["narration.turn.total_cost_usd"] == pytest.approx(0.067)
    assert attrs["narration.turn.tool_call_count"] == 3
```

- [ ] **Step 7.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/telemetry/test_narration_turn_cost_span.py -v
```

Expected: ImportError.

- [ ] **Step 7.3: Implement the rollup span module**

Create `sidequest-server/sidequest/telemetry/spans/cost.py`:
```python
"""OTEL span: narration.turn — rollup parent for one narrator turn.

Children: llm.request spans (Task 6) + tool.{read,write,gen}.* spans (Phase B).

Seeded attributes (entry):
    world_id, session_id, turn_number, acting_pc

Rollup attributes (set by caller before exit):
    narration.turn.model_chosen
    narration.turn.total_input_tokens
    narration.turn.total_output_tokens
    narration.turn.cache_read_tokens
    narration.turn.cache_write_tokens
    narration.turn.total_cost_usd
    narration.turn.tool_call_count
    narration.turn.llm_request_count
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

_TRACER = trace.get_tracer(__name__)


@contextmanager
def narration_turn_cost_span(
    *,
    world_id: str,
    session_id: str,
    turn_number: int,
    acting_pc: str,
) -> Iterator[Span]:
    with _TRACER.start_as_current_span("narration.turn") as span:
        span.set_attribute("world_id", world_id)
        span.set_attribute("session_id", session_id)
        span.set_attribute("turn_number", turn_number)
        span.set_attribute("acting_pc", acting_pc)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
```

- [ ] **Step 7.4: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/telemetry/test_narration_turn_cost_span.py -v
```

Expected: 3 passed.

- [ ] **Step 7.5: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/telemetry/spans/cost.py tests/telemetry/test_narration_turn_cost_span.py
uv run pyright sidequest/telemetry/spans/cost.py tests/telemetry/test_narration_turn_cost_span.py
```

Expected: no findings.

- [ ] **Step 7.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/telemetry/spans/cost.py tests/telemetry/test_narration_turn_cost_span.py
git commit -m "feat(telemetry): add narration.turn cost rollup OTEL span

Phase A foundation. Parent span for an entire narrator turn; children are
llm.request and tool.* spans. Rollup attrs set by the orchestrator after
the tool loop settles."
```

---

## Task 8 — `AnthropicSdkClient`: construction + auth + error types

**Files:**
- Create: `sidequest-server/sidequest/agents/anthropic_sdk_client.py`
- Test: `sidequest-server/tests/agents/test_anthropic_sdk_client.py`

Class skeleton + construction. The real `complete_with_tools` method ships in Task 9. Split intentionally: Task 8 nails down auth + error semantics + the seam where the SDK client gets injected (for tests), Task 9 adds the loop logic on top.

- [ ] **Step 8.1: Write the failing test**

Create `sidequest-server/tests/agents/test_anthropic_sdk_client.py`:
```python
"""Tests for AnthropicSdkClient — construction, auth, error semantics."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from sidequest.agents.anthropic_sdk_client import (
    AnthropicSdkClient,
    AnthropicSdkConfigError,
)
from sidequest.agents.tooling_protocol import ToolingLlmClient


def test_construction_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AnthropicSdkConfigError):
        AnthropicSdkClient()


def test_construction_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-1")
    client = AnthropicSdkClient()
    assert client.api_key_present is True


def test_construction_accepts_explicit_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake_sdk = MagicMock(name="AsyncAnthropic")
    client = AnthropicSdkClient(sdk=fake_sdk)
    assert client.api_key_present is False  # bypassed via explicit injection
    assert client._sdk is fake_sdk  # type: ignore[attr-defined]


def test_implements_tooling_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-1")
    client = AnthropicSdkClient()
    assert isinstance(client, ToolingLlmClient)


def test_default_cache_ttl_is_5_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-1")
    client = AnthropicSdkClient()
    assert client.cache_ttl == "5m"


def test_opt_into_1_hour_cache_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-1")
    monkeypatch.setenv("SIDEQUEST_ANTHROPIC_CACHE_TTL", "1h")
    client = AnthropicSdkClient()
    assert client.cache_ttl == "1h"


def test_invalid_cache_ttl_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-1")
    monkeypatch.setenv("SIDEQUEST_ANTHROPIC_CACHE_TTL", "banana")
    with pytest.raises(AnthropicSdkConfigError):
        AnthropicSdkClient()
```

- [ ] **Step 8.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_anthropic_sdk_client.py -v
```

Expected: ImportError.

- [ ] **Step 8.3: Implement the construction surface**

Create `sidequest-server/sidequest/agents/anthropic_sdk_client.py`:
```python
"""AnthropicSdkClient — Phase A foundation.

Construction, auth, cache-TTL config, and the ToolingLlmClient seam.
complete_with_tools lands in the next task (Task 9).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, Literal

from sidequest.agents.claude_client import LlmClientError
from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
    ToolDefinition,
    ToolingResult,
    ToolResultBlock,
    ToolUseBlock,
)


class AnthropicSdkClientError(LlmClientError):
    """Base error from AnthropicSdkClient."""


class AnthropicSdkConfigError(AnthropicSdkClientError):
    """Construction-time configuration problem (missing key, bad TTL)."""


CacheTtl = Literal["5m", "1h"]
_VALID_TTLS: frozenset[str] = frozenset({"5m", "1h"})


class AnthropicSdkClient:
    """Anthropic SDK client implementing ToolingLlmClient.

    Construction is loud: missing ANTHROPIC_API_KEY raises on any path that
    didn't inject `sdk=` directly. Tests inject; production reads env.
    """

    def __init__(
        self,
        *,
        sdk: Any | None = None,
        cache_ttl: CacheTtl | None = None,
    ) -> None:
        self._api_key = os.environ.get("ANTHROPIC_API_KEY")
        if sdk is None and not self._api_key:
            raise AnthropicSdkConfigError(
                "ANTHROPIC_API_KEY not set — required to construct "
                "AnthropicSdkClient without an explicit sdk= injection."
            )

        resolved_ttl: str
        if cache_ttl is not None:
            resolved_ttl = cache_ttl
        else:
            resolved_ttl = os.environ.get("SIDEQUEST_ANTHROPIC_CACHE_TTL", "5m")
        if resolved_ttl not in _VALID_TTLS:
            raise AnthropicSdkConfigError(
                f"SIDEQUEST_ANTHROPIC_CACHE_TTL={resolved_ttl!r} invalid; "
                f"must be one of {sorted(_VALID_TTLS)}"
            )
        self.cache_ttl: CacheTtl = resolved_ttl  # type: ignore[assignment]

        if sdk is None:
            from anthropic import AsyncAnthropic  # local import: avoid module load on test paths

            sdk = AsyncAnthropic(api_key=self._api_key)
        self._sdk = sdk

    @property
    def api_key_present(self) -> bool:
        return bool(self._api_key)

    async def complete_with_tools(
        self,
        system_blocks: list[CacheableBlock],
        messages: list[Message],
        tools: list[ToolDefinition],
        tool_dispatch: Callable[[ToolUseBlock], ToolResultBlock] | None = None,
        *,
        model: str,
        max_iterations: int = 8,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> ToolingResult:
        raise NotImplementedError(
            "complete_with_tools lands in Task 9. Phase A Task 8 only "
            "covers construction + protocol seam."
        )
```

- [ ] **Step 8.4: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_anthropic_sdk_client.py -v
```

Expected: 7 passed.

- [ ] **Step 8.5: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py
uv run pyright sidequest/agents/anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py
```

Expected: no findings.

- [ ] **Step 8.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py
git commit -m "feat(agents): add AnthropicSdkClient construction + auth + cache TTL

Phase A foundation. Construction reads ANTHROPIC_API_KEY (fails loud per
CLAUDE.md no-silent-fallbacks); SIDEQUEST_ANTHROPIC_CACHE_TTL accepts 5m
or 1h. complete_with_tools method raises NotImplementedError — wired in
the next task.

Refs spec §AnthropicSdkClient and caching strategy."
```

---

## Task 9 — `AnthropicSdkClient.complete_with_tools` — real loop

**Files:**
- Modify: `sidequest-server/sidequest/agents/anthropic_sdk_client.py`
- Test: `sidequest-server/tests/agents/test_anthropic_sdk_client.py` (extend)

Wires the tool-use loop against a duck-typed SDK shape. Tests inject a `FakeAsyncAnthropic` that mimics the SDK's `messages.create` / streaming surface — no real API calls.

- [ ] **Step 9.1: Add an SDK-shape test fake**

Append to `sidequest-server/tests/agents/test_anthropic_sdk_client.py`:
```python
# --- SDK-shape fake for complete_with_tools loop tests ----------------------

from dataclasses import dataclass, field

@dataclass(frozen=True)
class _Usage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass(frozen=True)
class _SdkContentTextBlock:
    type: str
    text: str


@dataclass(frozen=True)
class _SdkContentToolUseBlock:
    type: str
    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class _SdkResponse:
    content: list[Any]
    stop_reason: str
    usage: _Usage
    model: str


class _FakeSdkMessages:
    def __init__(self, responses: list[_SdkResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> _SdkResponse:
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("FakeSdkMessages: out of scripted responses")
        return self._responses.pop(0)


class _FakeAsyncSdk:
    def __init__(self, responses: list[_SdkResponse]) -> None:
        self.messages = _FakeSdkMessages(responses)


async def test_complete_with_tools_simple_end_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sdk_response = _SdkResponse(
        content=[_SdkContentTextBlock(type="text", text="The lantern gutters.")],
        stop_reason="end_turn",
        usage=_Usage(
            input_tokens=100,
            output_tokens=8,
            cache_read_input_tokens=80,
            cache_creation_input_tokens=0,
        ),
        model="claude-sonnet-4-6",
    )
    fake = _FakeAsyncSdk(responses=[sdk_response])
    client = AnthropicSdkClient(sdk=fake)
    result = await client.complete_with_tools(
        system_blocks=[CacheableBlock(text="rules", cache=True)],
        messages=[Message(role="user", content="hi")],
        tools=[],
        model="claude-sonnet-4-6",
    )
    assert result.text == "The lantern gutters."
    assert result.stop_reason == "end_turn"
    assert result.input_tokens == 100
    assert result.cached_input_read_tokens == 80
    assert len(fake.messages.calls) == 1


async def test_complete_with_tools_cache_control_on_last_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sdk_response = _SdkResponse(
        content=[_SdkContentTextBlock(type="text", text="ok")],
        stop_reason="end_turn",
        usage=_Usage(input_tokens=10, output_tokens=2),
        model="claude-sonnet-4-6",
    )
    fake = _FakeAsyncSdk(responses=[sdk_response])
    client = AnthropicSdkClient(sdk=fake)
    await client.complete_with_tools(
        system_blocks=[
            CacheableBlock(text="zone 1", cache=True),
            CacheableBlock(text="zone 2", cache=True),
            CacheableBlock(text="zone 3", cache=False),
        ],
        messages=[Message(role="user", content="hi")],
        tools=[],
        model="claude-sonnet-4-6",
    )
    call = fake.messages.calls[0]
    system = call["system"]
    # Two cache-marked blocks get cache_control markers.
    assert system[0]["cache_control"]["type"] == "ephemeral"
    assert system[1]["cache_control"]["type"] == "ephemeral"
    assert "cache_control" not in system[2]


async def test_complete_with_tools_runs_tool_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    first = _SdkResponse(
        content=[
            _SdkContentToolUseBlock(
                type="tool_use",
                id="toolu_1",
                name="roll_dice",
                input={"sides": 20},
            )
        ],
        stop_reason="tool_use",
        usage=_Usage(input_tokens=200, output_tokens=15),
        model="claude-sonnet-4-6",
    )
    second = _SdkResponse(
        content=[_SdkContentTextBlock(type="text", text="The roll landed.")],
        stop_reason="end_turn",
        usage=_Usage(input_tokens=220, output_tokens=10),
        model="claude-sonnet-4-6",
    )
    fake = _FakeAsyncSdk(responses=[first, second])
    client = AnthropicSdkClient(sdk=fake)

    def dispatch(block: ToolUseBlock) -> ToolResultBlock:
        return ToolResultBlock(tool_use_id=block.id, content="17", is_error=False)

    result = await client.complete_with_tools(
        system_blocks=[CacheableBlock(text="rules", cache=True)],
        messages=[Message(role="user", content="roll for it")],
        tools=[
            ToolDefinition(
                name="roll_dice",
                description="Roll",
                input_schema={"type": "object"},
            )
        ],
        tool_dispatch=dispatch,
        model="claude-sonnet-4-6",
    )
    assert result.text == "The roll landed."
    assert result.stop_reason == "end_turn"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "roll_dice"
    assert len(fake.messages.calls) == 2


async def test_complete_with_tools_respects_max_iterations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Infinite tool-use loop (would be a bug in the model in real life).
    def loop_response() -> _SdkResponse:
        return _SdkResponse(
            content=[
                _SdkContentToolUseBlock(
                    type="tool_use", id="x", name="roll_dice", input={}
                )
            ],
            stop_reason="tool_use",
            usage=_Usage(input_tokens=10, output_tokens=1),
            model="claude-sonnet-4-6",
        )

    fake = _FakeAsyncSdk(responses=[loop_response() for _ in range(20)])
    client = AnthropicSdkClient(sdk=fake)

    def dispatch(block: ToolUseBlock) -> ToolResultBlock:
        return ToolResultBlock(tool_use_id=block.id, content="ok")

    with pytest.raises(AnthropicSdkClientError):
        await client.complete_with_tools(
            system_blocks=[CacheableBlock(text="r")],
            messages=[Message(role="user", content="hi")],
            tools=[
                ToolDefinition(
                    name="roll_dice", description="r", input_schema={"type": "object"}
                )
            ],
            tool_dispatch=dispatch,
            model="claude-sonnet-4-6",
            max_iterations=3,
        )


async def test_complete_with_tools_records_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cost arithmetic happens via compute_cost_usd; client surfaces buckets."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sdk_response = _SdkResponse(
        content=[_SdkContentTextBlock(type="text", text="x")],
        stop_reason="end_turn",
        usage=_Usage(
            input_tokens=200,
            output_tokens=100,
            cache_read_input_tokens=800,
            cache_creation_input_tokens=50,
        ),
        model="claude-sonnet-4-6",
    )
    fake = _FakeAsyncSdk(responses=[sdk_response])
    client = AnthropicSdkClient(sdk=fake)
    result = await client.complete_with_tools(
        system_blocks=[CacheableBlock(text="r", cache=True)],
        messages=[Message(role="user", content="hi")],
        tools=[],
        model="claude-sonnet-4-6",
    )
    assert result.cached_input_read_tokens == 800
    assert result.cached_input_write_tokens == 50


async def test_complete_with_tools_imports_anthropic_sdk_error_types() -> None:
    """Ensure AnthropicSdkClientError exists and is wired."""
    assert issubclass(AnthropicSdkClientError, Exception)
```

Also add the import at the top of the test file:
```python
from sidequest.agents.anthropic_sdk_client import AnthropicSdkClientError
```

- [ ] **Step 9.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_anthropic_sdk_client.py -v
```

Expected: tests in this task fail with `NotImplementedError` (from Task 8 stub).

- [ ] **Step 9.3: Implement `complete_with_tools` + cache_control wiring**

Replace the body of `complete_with_tools` in `sidequest-server/sidequest/agents/anthropic_sdk_client.py` and add helper methods. The full updated file:

```python
"""AnthropicSdkClient — Phase A foundation."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, Literal

from sidequest.agents.anthropic_cost import compute_cost_usd
from sidequest.agents.claude_client import LlmClientError
from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
    ToolDefinition,
    ToolingResult,
    ToolResultBlock,
    ToolUseBlock,
)
from sidequest.telemetry.spans.llm_request import llm_request_span


class AnthropicSdkClientError(LlmClientError):
    """Base error from AnthropicSdkClient."""


class AnthropicSdkConfigError(AnthropicSdkClientError):
    """Construction-time configuration problem (missing key, bad TTL)."""


class AnthropicSdkLoopExceeded(AnthropicSdkClientError):
    """The tool-use loop did not converge within max_iterations."""


CacheTtl = Literal["5m", "1h"]
_VALID_TTLS: frozenset[str] = frozenset({"5m", "1h"})


class AnthropicSdkClient:
    """Anthropic SDK client implementing ToolingLlmClient."""

    def __init__(
        self,
        *,
        sdk: Any | None = None,
        cache_ttl: CacheTtl | None = None,
    ) -> None:
        self._api_key = os.environ.get("ANTHROPIC_API_KEY")
        if sdk is None and not self._api_key:
            raise AnthropicSdkConfigError(
                "ANTHROPIC_API_KEY not set — required to construct "
                "AnthropicSdkClient without an explicit sdk= injection."
            )

        resolved_ttl = (
            cache_ttl
            if cache_ttl is not None
            else os.environ.get("SIDEQUEST_ANTHROPIC_CACHE_TTL", "5m")
        )
        if resolved_ttl not in _VALID_TTLS:
            raise AnthropicSdkConfigError(
                f"SIDEQUEST_ANTHROPIC_CACHE_TTL={resolved_ttl!r} invalid; "
                f"must be one of {sorted(_VALID_TTLS)}"
            )
        self.cache_ttl: CacheTtl = resolved_ttl  # type: ignore[assignment]

        if sdk is None:
            from anthropic import AsyncAnthropic

            sdk = AsyncAnthropic(api_key=self._api_key)
        self._sdk = sdk

    @property
    def api_key_present(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------
    # complete_with_tools
    # ------------------------------------------------------------------

    async def complete_with_tools(
        self,
        system_blocks: list[CacheableBlock],
        messages: list[Message],
        tools: list[ToolDefinition],
        tool_dispatch: Callable[[ToolUseBlock], ToolResultBlock] | None = None,
        *,
        model: str,
        max_iterations: int = 8,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> ToolingResult:
        sdk_system = self._build_system_array(system_blocks)
        sdk_tools = self._build_tools_array(tools)

        running_messages: list[dict[str, Any]] = [
            {"role": m.role, "content": m.content} for m in messages
        ]
        all_tool_uses: list[ToolUseBlock] = []
        last_text = ""
        cumulative_in = 0
        cumulative_out = 0
        cumulative_cache_read = 0
        cumulative_cache_write = 0
        last_model = model

        for iteration in range(1, max_iterations + 1):
            with llm_request_span(model=model, iteration=iteration) as span:
                response = await self._sdk.messages.create(
                    model=model,
                    system=sdk_system,
                    messages=running_messages,
                    tools=sdk_tools,
                    max_tokens=4096,
                )
                usage = response.usage
                input_tokens = int(getattr(usage, "input_tokens", 0))
                output_tokens = int(getattr(usage, "output_tokens", 0))
                cache_read = int(getattr(usage, "cache_read_input_tokens", 0))
                cache_write = int(getattr(usage, "cache_creation_input_tokens", 0))
                cumulative_in += input_tokens
                cumulative_out += output_tokens
                cumulative_cache_read += cache_read
                cumulative_cache_write += cache_write
                last_model = response.model

                cost = compute_cost_usd(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_read_tokens=cache_read,
                    cached_input_write_tokens=cache_write,
                    model=response.model,
                )
                span.set_attributes(
                    {
                        "llm.input_tokens": input_tokens,
                        "llm.output_tokens": output_tokens,
                        "llm.cached_input_read_tokens": cache_read,
                        "llm.cached_input_write_tokens": cache_write,
                        "llm.stop_reason": response.stop_reason,
                        "llm.cost_usd": cost,
                    }
                )

            text_chunks, tool_use_blocks = self._split_content(response.content)
            text = "".join(text_chunks)
            if on_text_delta is not None and text:
                on_text_delta(text)
            last_text = text or last_text

            if response.stop_reason != "tool_use":
                return ToolingResult(
                    text=last_text,
                    stop_reason=response.stop_reason,
                    input_tokens=cumulative_in,
                    output_tokens=cumulative_out,
                    cached_input_read_tokens=cumulative_cache_read,
                    cached_input_write_tokens=cumulative_cache_write,
                    model=last_model,
                    tool_calls=all_tool_uses,
                )

            if tool_dispatch is None:
                raise AnthropicSdkClientError(
                    "Model emitted tool_use but no tool_dispatch was provided."
                )

            assistant_blocks: list[dict[str, Any]] = []
            user_results: list[dict[str, Any]] = []
            for tu in tool_use_blocks:
                all_tool_uses.append(tu)
                assistant_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tu.id,
                        "name": tu.name,
                        "input": tu.arguments,
                    }
                )
                result = tool_dispatch(tu)
                user_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": result.tool_use_id,
                        "content": result.content,
                        "is_error": result.is_error,
                    }
                )
            running_messages = running_messages + [
                {"role": "assistant", "content": assistant_blocks},
                {"role": "user", "content": user_results},
            ]

        raise AnthropicSdkLoopExceeded(
            f"Tool-use loop did not converge in {max_iterations} iterations"
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _build_system_array(
        self, system_blocks: list[CacheableBlock]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for block in system_blocks:
            entry: dict[str, Any] = {"type": "text", "text": block.text}
            if block.cache:
                cache_control: dict[str, Any] = {"type": "ephemeral"}
                if self.cache_ttl == "1h":
                    cache_control["ttl"] = "1h"
                entry["cache_control"] = cache_control
            out.append(entry)
        return out

    def _build_tools_array(
        self, tools: list[ToolDefinition]
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]

    @staticmethod
    def _split_content(
        content: list[Any],
    ) -> tuple[list[str], list[ToolUseBlock]]:
        text_chunks: list[str] = []
        tool_uses: list[ToolUseBlock] = []
        for block in content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_chunks.append(getattr(block, "text", ""))
            elif block_type == "tool_use":
                tool_uses.append(
                    ToolUseBlock(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )
        return text_chunks, tool_uses
```

- [ ] **Step 9.4: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_anthropic_sdk_client.py -v
```

Expected: all 13 tests pass (7 from Task 8 + 6 new).

- [ ] **Step 9.5: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py
uv run pyright sidequest/agents/anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py
```

Expected: no findings.

- [ ] **Step 9.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py
git commit -m "feat(agents): implement AnthropicSdkClient.complete_with_tools

Phase A foundation. Tool-use loop with cache_control on cacheable system
blocks, per-iteration llm.request OTEL spans with token/cache/cost attrs,
max_iterations enforcement, and clean ToolingResult assembly.

cache_ttl='1h' adds {ttl: '1h'} to cache_control entries (beta opt-in).
Cost arithmetic delegates to compute_cost_usd."
```

---

## Task 10 — Wiring test: SDK client through `complete_with_tools` end-to-end

**Files:**
- Create: `sidequest-server/tests/agents/test_anthropic_sdk_client_wiring.py`

The "every test suite needs a wiring test" mandate (CLAUDE.md). Exercises: SDK client + protocol + cost math + telemetry span emission + tool round-trip + on_text_delta — all in one scenario, no module mocking.

- [ ] **Step 10.1: Write the wiring test**

Create `sidequest-server/tests/agents/test_anthropic_sdk_client_wiring.py`:
```python
"""Wiring test for Phase A — SDK client through tool round-trip + spans.

Exercises every Phase A primitive together: protocol dataclasses, the
SDK client, cost math, llm.request span emission, cache_control on
system blocks, the tool loop, and streaming text deltas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.agents.anthropic_sdk_client import AnthropicSdkClient
from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
    ToolDefinition,
    ToolResultBlock,
    ToolUseBlock,
)


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class _TextBlock:
    type: str
    text: str


@dataclass
class _ToolUseBlock:
    type: str
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class _Response:
    content: list[Any]
    stop_reason: str
    usage: _Usage
    model: str


class _Messages:
    def __init__(self, responses: list[_Response]) -> None:
        self._responses = responses
        self.received: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> _Response:
        self.received.append(kwargs)
        return self._responses.pop(0)


class _Sdk:
    def __init__(self, responses: list[_Response]) -> None:
        self.messages = _Messages(responses)


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    trace.set_tracer_provider(provider)
    return exp


async def test_combat_shaped_turn_wiring(
    exporter: InMemorySpanExporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    sdk = _Sdk(
        responses=[
            _Response(
                content=[
                    _ToolUseBlock(
                        type="tool_use",
                        id="toolu_a",
                        name="roll_dice",
                        input={"sides": 20},
                    )
                ],
                stop_reason="tool_use",
                usage=_Usage(
                    input_tokens=300,
                    output_tokens=20,
                    cache_read_input_tokens=12000,
                    cache_creation_input_tokens=0,
                ),
                model="claude-sonnet-4-6",
            ),
            _Response(
                content=[
                    _TextBlock(
                        type="text",
                        text="The strike lands; the bandit reels.",
                    )
                ],
                stop_reason="end_turn",
                usage=_Usage(
                    input_tokens=350,
                    output_tokens=80,
                    cache_read_input_tokens=12000,
                    cache_creation_input_tokens=0,
                ),
                model="claude-sonnet-4-6",
            ),
        ]
    )
    client = AnthropicSdkClient(sdk=sdk, cache_ttl="1h")

    deltas: list[str] = []

    def dispatch(block: ToolUseBlock) -> ToolResultBlock:
        assert block.name == "roll_dice"
        return ToolResultBlock(tool_use_id=block.id, content="17")

    result = await client.complete_with_tools(
        system_blocks=[
            CacheableBlock(text="SOUL+rules+tone", cache=True),
            CacheableBlock(text="tool defs", cache=True),
            CacheableBlock(text="world snapshot", cache=True),
        ],
        messages=[
            Message(role="user", content="I swing for the bandit."),
        ],
        tools=[
            ToolDefinition(
                name="roll_dice",
                description="Roll polyhedral dice",
                input_schema={
                    "type": "object",
                    "properties": {"sides": {"type": "integer"}},
                    "required": ["sides"],
                },
            )
        ],
        tool_dispatch=dispatch,
        model="claude-sonnet-4-6",
        on_text_delta=deltas.append,
    )

    # 1. Final narration came through.
    assert result.text == "The strike lands; the bandit reels."
    assert result.stop_reason == "end_turn"

    # 2. Token rollups are cumulative across iterations.
    assert result.input_tokens == 650
    assert result.output_tokens == 100
    assert result.cached_input_read_tokens == 24000

    # 3. Tool round-trip captured.
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "roll_dice"

    # 4. Streaming callback got the final-turn text.
    assert deltas == ["The strike lands; the bandit reels."]

    # 5. Cache_control with 1h TTL flows into the SDK call.
    first_call = sdk.messages.received[0]
    sys_array = first_call["system"]
    assert sys_array[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}

    # 6. Two llm.request spans emitted (one per iteration).
    spans = [s for s in exporter.get_finished_spans() if s.name == "llm.request"]
    assert len(spans) == 2
    iter_attrs = sorted(int((s.attributes or {})["llm.iteration"]) for s in spans)
    assert iter_attrs == [1, 2]

    # 7. Cost attribute non-zero and computed against the cost module.
    first_attrs = dict(spans[0].attributes or {})
    assert first_attrs["llm.cost_usd"] > 0
```

- [ ] **Step 10.2: Run the wiring test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_anthropic_sdk_client_wiring.py -v
```

Expected: 1 passed.

- [ ] **Step 10.3: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check tests/agents/test_anthropic_sdk_client_wiring.py
uv run pyright tests/agents/test_anthropic_sdk_client_wiring.py
```

Expected: no findings.

- [ ] **Step 10.4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add tests/agents/test_anthropic_sdk_client_wiring.py
git commit -m "test(agents): add Phase A end-to-end wiring test

Combat-shaped tool round-trip exercising every Phase A primitive together:
protocol dataclasses, SDK client, cost math, llm.request span emission,
cache_control with 1h TTL, tool dispatch, and on_text_delta. No module
mocking — only the SDK boundary is faked. Satisfies CLAUDE.md
'every test suite needs a wiring test' mandate."
```

---

## Task 11 — Expose `AnthropicSdkClient` via factory (gated)

**Files:**
- Modify: `sidequest-server/sidequest/agents/llm_factory.py`
- Test: `sidequest-server/tests/agents/test_llm_factory.py` (extend)

Adds `anthropic_sdk` as a valid backend key. **Does not** become the default — narrator path still resolves to `claude` via `build_llm_client`. This is a *seam*, not a switchover. Phase E flips the default.

- [ ] **Step 11.1: Look at the existing factory test layout**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
head -60 tests/agents/test_llm_factory.py
```

- [ ] **Step 11.2: Extend the factory test**

Append to `sidequest-server/tests/agents/test_llm_factory.py`:
```python
def test_anthropic_sdk_backend_key_routes_to_sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sidequest.agents.anthropic_sdk_client import AnthropicSdkClient
    from sidequest.agents.llm_factory import build_llm_client

    monkeypatch.setenv("SIDEQUEST_LLM_BACKEND", "anthropic_sdk")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    client = build_llm_client()
    assert isinstance(client, AnthropicSdkClient)


def test_default_is_still_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    from sidequest.agents.claude_client import ClaudeClient
    from sidequest.agents.llm_factory import build_llm_client

    monkeypatch.delenv("SIDEQUEST_LLM_BACKEND", raising=False)
    client = build_llm_client()
    assert isinstance(client, ClaudeClient)
```

(Adjust the `pytest` import at top of file if not already present.)

- [ ] **Step 11.3: Run the failing tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_llm_factory.py -v
```

Expected: `test_anthropic_sdk_backend_key_routes_to_sdk_client` fails with `UnknownBackend`.

- [ ] **Step 11.4: Wire the factory**

Edit `sidequest-server/sidequest/agents/llm_factory.py`:

Change the imports block to also import the SDK client:
```python
from sidequest.agents.anthropic_sdk_client import AnthropicSdkClient
from sidequest.agents.claude_client import ClaudeClient, LlmClient, LlmClientError
from sidequest.agents.ollama_client import DEFAULT_OLLAMA_URL, OllamaClient
```

Update the valid-backends set:
```python
_VALID_BACKENDS = frozenset({"claude", "ollama", "anthropic_sdk"})
```

And add the dispatch arm in `build_llm_client` after the `ollama` arm:
```python
    if key == "anthropic_sdk":
        return AnthropicSdkClient()
```

- [ ] **Step 11.5: Run the tests to verify they pass**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_llm_factory.py -v
```

Expected: all tests pass.

- [ ] **Step 11.6: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/llm_factory.py tests/agents/test_llm_factory.py
uv run pyright sidequest/agents/llm_factory.py
```

Expected: no findings.

- [ ] **Step 11.7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/llm_factory.py tests/agents/test_llm_factory.py
git commit -m "feat(agents): wire 'anthropic_sdk' backend key in llm_factory

Phase A foundation. SIDEQUEST_LLM_BACKEND=anthropic_sdk now returns an
AnthropicSdkClient. Default remains 'claude' — narrator path is
unchanged until Phase E flips the default. This is a seam, not a
cutover."
```

---

## Task 12 — Public agents `__init__` exports

**Files:**
- Modify: `sidequest-server/sidequest/agents/__init__.py`
- Test: `sidequest-server/tests/agents/test_agents_exports.py` (extend)

Make `AnthropicSdkClient`, `ToolingLlmClient`, the protocol dataclasses, and `CallType`/`resolve_model` importable from `sidequest.agents` so downstream callers don't reach into submodules. **Do not** export `FakeAnthropicSdkClient` — that lives under `tests/` only.

- [ ] **Step 12.1: Read existing exports**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
cat sidequest/agents/__init__.py
```

- [ ] **Step 12.2: Extend the exports test**

Append to `sidequest-server/tests/agents/test_agents_exports.py`:
```python
def test_anthropic_sdk_client_exported() -> None:
    from sidequest.agents import AnthropicSdkClient

    assert AnthropicSdkClient is not None


def test_tooling_protocol_exports() -> None:
    from sidequest.agents import (
        CacheableBlock,
        Message,
        ToolDefinition,
        ToolingLlmClient,
        ToolingResult,
        ToolResultBlock,
        ToolUseBlock,
    )

    assert all(
        x is not None
        for x in (
            CacheableBlock,
            Message,
            ToolDefinition,
            ToolingLlmClient,
            ToolingResult,
            ToolResultBlock,
            ToolUseBlock,
        )
    )


def test_call_type_and_resolver_exported() -> None:
    from sidequest.agents import CallType, resolve_model

    assert resolve_model(CallType.NARRATION) == "claude-sonnet-4-6"
```

- [ ] **Step 12.3: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_agents_exports.py -v
```

Expected: ImportErrors on the new tests.

- [ ] **Step 12.4: Add exports to `agents/__init__.py`**

Append (keep all existing exports — do not delete):
```python
from sidequest.agents.anthropic_sdk_client import (
    AnthropicSdkClient,
    AnthropicSdkClientError,
    AnthropicSdkConfigError,
    AnthropicSdkLoopExceeded,
)
from sidequest.agents.model_routing import CallType, resolve_model
from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
    ToolDefinition,
    ToolingLlmClient,
    ToolingResult,
    ToolResultBlock,
    ToolUseBlock,
)
```

- [ ] **Step 12.5: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_agents_exports.py -v
```

Expected: all tests pass.

- [ ] **Step 12.6: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/__init__.py
uv run pyright sidequest/agents/__init__.py
```

Expected: no findings.

- [ ] **Step 12.7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/__init__.py tests/agents/test_agents_exports.py
git commit -m "feat(agents): export Phase A foundation symbols

AnthropicSdkClient + error types, tooling protocol dataclasses, CallType
+ resolve_model now importable from sidequest.agents. FakeAnthropicSdkClient
intentionally not exported — test-only."
```

---

## Task 13 — Phase A acceptance: full sweep

**Files:** none modified

Confirm Phase A is green before declaring done.

- [ ] **Step 13.1: Run the server gate**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v
```

Expected: 100% pass; no skips beyond pre-existing.

- [ ] **Step 13.2: Lint sweep**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check .
uv run ruff format --check .
```

Expected: clean.

- [ ] **Step 13.3: Type-check sweep**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pyright
```

Expected: zero new errors. (Track baseline if pyright already has known findings.)

- [ ] **Step 13.4: Orchestrator-level gate**

```bash
cd /Users/slabgorb/Projects/oq-1/
just check-all
```

Expected: green across server, client, daemon (server is the only repo Phase A touches; UI + daemon should stay green).

- [ ] **Step 13.5: Push the feature branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git push -u origin feat/anthropic-sdk-migration
```

Expected: branch published. **Do not open a PR to `develop`** — Phase E does that after Phases B+C+D land.

---

## Task 14 — ADR-099 draft

**Files:**
- Create: `orc-quest/docs/adr/099-anthropic-sdk-as-narrator-backend.md`
- Modify: `orc-quest/docs/adr/001-claude-cli-only.md` (frontmatter only)
- Modify: `orc-quest/docs/adr/README.md` (via regen script)

Status remains **proposed** until Phase E merges. Lives on the orchestrator's `feat/anthropic-sdk-migration` branch so the ADR lands alongside the server merge.

- [ ] **Step 14.1: Create the orchestrator feature branch**

```bash
cd /Users/slabgorb/Projects/oq-1/
git fetch origin
git checkout main
git pull --ff-only
git checkout -b feat/anthropic-sdk-migration
```

- [ ] **Step 14.2: Inspect ADR frontmatter conventions**

```bash
cd /Users/slabgorb/Projects/oq-1/
head -25 docs/adr/088-adr-frontmatter-schema.md
head -20 docs/adr/067-unified-narrator-agent.md
```

Match the frontmatter schema exactly. The new ADR must include: `id`, `title`, `status: proposed`, `date: 2026-05-15`, `categories: [Core Architecture, Agent System]`, `supersedes: [001, 039, 058, 028]`, `amends: [073]`, `depends_on: [067, 098, 073]`.

- [ ] **Step 14.3: Write ADR-099**

Create `orc-quest/docs/adr/099-anthropic-sdk-as-narrator-backend.md`:

```markdown
---
id: 99
title: Anthropic SDK as Narrator Backend
status: proposed
date: 2026-05-15
categories:
  - Core Architecture
  - Agent System
supersedes: [1, 39, 58, 28]
amends: [73]
depends_on: [67, 98, 73]
load_bearing: true
---

# ADR-099: Anthropic SDK as Narrator Backend

## Status

Proposed. Promotes to **accepted** when `feat/anthropic-sdk-migration`
squash-merges to `develop` at the end of Phase E.

## Context

ADR-001 mandated `claude -p` subprocess calls as the only LLM transport. On
2026-06-15 Anthropic moves `claude -p` into a separate metered "programmatic
credit" pool, billed at API list rates and capped per subscription tier. At
typical playgroup load (200-300 turns × ~30k input / 2k output per turn,
uncached), one weekly session burns $24-36, pushing $96-144/month against a
$200 Max-20× cap. The current path is economically unsustainable post-cutover.

Three secondary problems compound:

1. `claude -p` cannot call tools mid-generation. Every structured output
   (dice, state patches, journal entries, disposition updates, scenario
   advances) routes through ADR-039's fenced-JSON sidecar — a ~200-LOC
   malformed-JSON parser, and a hallucination surface (the narrator can write
   prose claiming an effect with no matching sidecar field).
2. `claude -p` cannot use prompt caching. Every turn pays the full system-
   prompt tax (~25-50k tokens uncached).
3. ADR-058's OTEL passthrough is structurally forensic — it scrapes stderr
   JSON after the fact. ADR-031's "GM panel as lie detector" can only flag
   patterns post-narration.

## Decision

Migrate the narrator path to the Anthropic SDK on a single feature branch
(`feat/anthropic-sdk-migration`, Approach B from the design spec). `develop`
stays on `claude -p` until Phase E merge. The new path captures:

1. **Prompt caching** — `cache_control` markers on three system zones
   (SOUL + rules, tool definitions, world snapshot). Median 60% of input
   tokens cached after warmup; cached input is 90% cheaper than fresh input.
2. **Tool use** — JSON-Schema-validated tool round-trips replace the ADR-039
   sidecar. 26 tools in the v1 catalog cover every sidecar field.
3. **Just-in-time retrieval** — narrator queries subsystems only when each
   turn engages them; prompt-stuffing of unused content ends.
4. **Per-call model routing** — Haiku 4.5 for classification + scratch,
   Sonnet 4.6 for narration, Opus 4.7 for declared-important moments.

Combined target: weighted-average $0.05-0.07 per turn vs. ~$0.12 on
post-cutover `claude -p`. A 250-turn session costs $12-18; a Max-20× cap
covers ~12-14 sessions/month with margin.

The decision is structurally enabling for three additional cleanups,
documented in their respective successor ADRs:
- **ADR-100-successor** (tool-use protocol) — supersedes ADR-039
- **ADR-101-successor** (native OTEL via tool registry) — supersedes ADR-058
- **ADR-102-successor** (perception filtering at the tool layer) — supersedes
  ADR-028

(Successor numbers will be assigned at write-time during Phase D5.)

## Consequences

**Positive:**
- Per-turn cost drops to a level that fits the Max-20× cap with margin for
  dev playtests
- Sidecar parser deleted (Phase D); narration / mechanics divergence
  becomes structurally impossible — the narrator cannot describe a
  mechanical effect without invoking the corresponding tool
- ADR-028 post-pass perception rewriter deleted (Phase D); multiplayer turns
  drop from N+1 model calls to N
- GM panel becomes a structural lie detector — three new verification
  classes (mechanical assertion without action, state described without
  query, perception filter violation) become enforceable
- Prompt cache breakpoints align with existing prompt zones; little
  architectural rework needed beyond the slim pass

**Negative:**
- `ANTHROPIC_API_KEY` becomes a hard runtime requirement on narrator paths
  (no silent fallback — fail loud per CLAUDE.md)
- Tool selection becomes a quality surface — bad tool descriptions or
  overlapping tools degrade narration; mitigated by Phase C per-tool tuning
  with playtest fixtures
- Branch hygiene cost — `feat/anthropic-sdk-migration` rebases weekly
  against `develop` for 3-4 sprints
- Once Phase D deletes the sidecar parser, `SIDEQUEST_LLM_BACKEND=claude` is
  no longer a working narrator backend — the merge is a one-way door

**Neutral:**
- `ClaudeClient` and `OllamaClient` remain in place for non-narrator paths
  (mood classifier, name gen, scratch jobs)
- ADR-073 (LLM backend factory) is amended in scope, not retired — the
  factory still exists; the narrator path just stops being a configuration
  point

## Alternatives considered

**Approach A — Sequential cutover.** Backend swap + caching land first as a
self-contained change to `develop`; tool conversions follow in batches.
Lower per-change risk, but the prompt stays fat through the intermediate
window (no slim wins until later), and intermediate states ship to the
playgroup.

**Approach C — Strangler-fig coexistence.** SDK and CLI clients run side-by-
side on `develop`; tools land one at a time, each independently mergeable.
Rejected because mid-conversion playtests produce variable game quality the
playgroup will notice, and 25+ incremental merges create a heavier rebase
burden than one squash-merge from a feature branch.

**Approach B — Single big-bang on feature branch (selected).** `develop` is
protected throughout; the migration's design coherence (sidecar parser,
perception rewriter, and OTEL scraper deleted together) is achievable;
single squash-merge gives a clean revert path.

## References

- Design spec: `docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md`
- Phase A plan: `docs/superpowers/plans/2026-05-15-anthropic-sdk-migration-phase-a-foundation.md`
- ADR-001 (Claude CLI Only) — superseded on landing
- ADR-039 (JSON sidecar) — superseded on landing
- ADR-058 (Claude subprocess OTEL passthrough) — superseded on landing
- ADR-028 (Perception rewriter) — superseded on landing
- ADR-073 (LLM backend factory) — amended on landing
```

- [ ] **Step 14.4: Mark ADR-001 as superseded-by 099 (frontmatter only)**

Edit `orc-quest/docs/adr/001-claude-cli-only.md`. Locate the YAML frontmatter at the top of the file and add a `superseded_by: 99` field (do **not** change `status` to `superseded` — that flips only after Phase E merges). Do not edit the body.

- [ ] **Step 14.5: Regenerate the ADR index**

```bash
cd /Users/slabgorb/Projects/oq-1/
python scripts/regenerate_adr_indexes.py
```

Expected: `docs/adr/README.md` and the index block in `CLAUDE.md` updated to list ADR-099. If the script doesn't exist at that path, locate it:
```bash
cd /Users/slabgorb/Projects/oq-1/
find . -name 'regenerate_adr_indexes*' -not -path '*/node_modules/*' -not -path '*/.venv/*'
```
Run whatever it surfaces.

- [ ] **Step 14.6: Sanity-check the regen output**

```bash
cd /Users/slabgorb/Projects/oq-1/
grep -n "ADR-099\|099 " docs/adr/README.md | head -5
```

Expected: at least one line referencing ADR-099 in the proposed/Core Architecture/Agent System category.

- [ ] **Step 14.7: Commit the ADR**

```bash
cd /Users/slabgorb/Projects/oq-1/
git add docs/adr/099-anthropic-sdk-as-narrator-backend.md docs/adr/001-claude-cli-only.md docs/adr/README.md CLAUDE.md
git commit -m "docs(adr): add ADR-099 — Anthropic SDK as Narrator Backend (proposed)

Successor to ADR-001 (Claude CLI Only). Stays *proposed* until
feat/anthropic-sdk-migration squash-merges to develop at the end of
Phase E. ADR-001 gets a superseded_by: 99 frontmatter pointer (status
unchanged — flips on merge).

Refs spec: docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md
Refs plan: docs/superpowers/plans/2026-05-15-anthropic-sdk-migration-phase-a-foundation.md"
```

- [ ] **Step 14.8: Push the orchestrator branch**

```bash
cd /Users/slabgorb/Projects/oq-1/
git push -u origin feat/anthropic-sdk-migration
```

Expected: branch published. No PR opened.

---

## Phase A completion check

- [ ] **All 14 tasks committed.**
- [ ] **Two branches pushed:** `feat/anthropic-sdk-migration` on `sidequest-server` and on `orc-quest`.
- [ ] **No PRs opened.** Phase E opens the PR at the end of the migration.
- [ ] **Develop is unchanged.** `git log develop..feat/anthropic-sdk-migration --oneline` on each repo should show all the Phase A commits; the playgroup plays on `develop`.
- [ ] **The narrator still runs on `claude -p`.** `build_llm_client()` with no env override still returns `ClaudeClient`. Confirm:
  ```bash
  cd /Users/slabgorb/Projects/oq-1/sidequest-server
  uv run python -c "from sidequest.agents.llm_factory import build_llm_client; print(type(build_llm_client()).__name__)"
  ```
  Expected: `ClaudeClient`.
- [ ] **The new backend works behind the env flag.**
  ```bash
  cd /Users/slabgorb/Projects/oq-1/sidequest-server
  SIDEQUEST_LLM_BACKEND=anthropic_sdk ANTHROPIC_API_KEY=sk-fake uv run python -c "from sidequest.agents.llm_factory import build_llm_client; print(type(build_llm_client()).__name__)"
  ```
  Expected: `AnthropicSdkClient`.

Phase A is **done** when all of the above are true.

---

## What's next (out of scope for this plan)

- **Phase B** — Registry + `@tool` decorator + `ToolContext` + `ToolResult` + dispatch + `PerceptionFilter` primitive + tool-call OTEL spans (3 stories, 18 pts)
- **Phase C** — 26 tool conversions, risk-ordered (26 stories, ~52-78 pts)
- **Phase D** — Sidecar parser deletion, ADR-028 rewriter deletion, ADR-058 scraping deletion, final prompt slim, successor ADRs (5 stories, 16 pts)
- **Phase E** — Scenario baseline replay, live playgroup session, squash-merge to `develop` (3 stories, 7 pts)

Each phase will get its own plan written after the prior phase merges to the feature branch, so each plan reflects the actual state of `feat/anthropic-sdk-migration` at the time it's written rather than a forecast.
