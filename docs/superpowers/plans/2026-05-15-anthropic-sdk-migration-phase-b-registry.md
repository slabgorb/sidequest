# Anthropic SDK Migration — Phase B: Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the tool registry, `@tool` decorator, `ToolContext`/`ToolResult`/`PerceptionFilter` primitives, dispatch (with parallel `read`/`gen` and serialized `write`), and tool-call OTEL spans. Registry is callable end-to-end via the SDK client built in Phase A, but has zero tools registered — Phase C populates the v1 catalog.

**Architecture:** The registry is a thin name→handler dispatcher. Tools are registered at import time via a `@tool(name, description, category)` decorator that appends to a module-level list. `ToolContext` carries injected runtime state the model never sees (world_id, session_id, perspective_pc, sqlite store, parent OTEL span, perception filter). `ToolResult` is a discriminated union with three variants (`ok` / `not_found` / `error`). Dispatch wraps each handler in a `tool.{read,write,gen}.{name}` OTEL span; writes serialize per session via `asyncio.Lock`; reads/generates run in parallel via `asyncio.gather`.

**Tech Stack:** Same as Phase A (Python 3.12, Pydantic 2, pytest-asyncio, OpenTelemetry).

**Scope:** Phase B only — 3 stories (B1-B3, ~18 pts). Phase A must be merged to the feature branch before this plan starts. Phase C (26 tool conversions) depends on the primitives this phase ships.

**Branch:** `feat/anthropic-sdk-migration` (same branch as Phase A) in `sidequest-server/`.

---

## File Structure

**Created:**
- `sidequest-server/sidequest/agents/tool_registry.py` — `@tool` decorator, `Registry` class, `ToolContext` dataclass, `ToolResult` factory, dispatch entry point
- `sidequest-server/sidequest/agents/perception_filter.py` — `PerceptionFilter` Protocol + `NoopPerceptionFilter` default + per-call hook signatures
- `sidequest-server/sidequest/agents/tools/__init__.py` — empty barrel; Phase C imports each tool module here
- `sidequest-server/sidequest/telemetry/spans/tool_dispatch.py` — `tool_dispatch_span` context manager with `tool.name`, `tool.category`, `tool.result_status`, `tool.duration_ms`, `tool.result_size_bytes`, `tool.perspective_pc`, `tool.cache_invalidates` attributes
- `sidequest-server/tests/agents/test_tool_registry.py`
- `sidequest-server/tests/agents/test_tool_registry_wiring.py`
- `sidequest-server/tests/agents/test_perception_filter.py`
- `sidequest-server/tests/telemetry/test_tool_dispatch_span.py`

**Modified:**
- `sidequest-server/sidequest/agents/__init__.py` — export `Registry`, `tool`, `ToolContext`, `ToolResult`, `PerceptionFilter`, `NoopPerceptionFilter`

---

## Self-Review (pre-execution)

Spec coverage:
- B1 → Tasks 1-4 (registry + decorator + context + result + dispatch)
- B2 → Task 5 (PerceptionFilter primitive)
- B3 → Tasks 6-7 (OTEL span + cost attrs already on llm.request from Phase A)

Type consistency:
- `ToolContext` fields (`world_id`, `session_id`, `perspective_pc`, `turn_number`, `store`, `otel_span`, `perception_filter`) used in Tasks 1-4 with same names.
- `ToolResult.ok()` / `not_found()` / `error()` constructors used in registry tests + wiring test + perception filter tests with identical signatures.

Placeholder scan: none. Every task shows the actual code.

---

## Task 1 — `ToolContext` + `ToolResult` primitives

**Files:**
- Create: `sidequest-server/sidequest/agents/tool_registry.py` (partial — primitives only)
- Test: `sidequest-server/tests/agents/test_tool_registry.py` (primitive tests)

- [ ] **Step 1.1: Write the failing test**

Create `sidequest-server/tests/agents/test_tool_registry.py`:
```python
"""Tests for tool_registry primitives — ToolContext, ToolResult, Registry."""

from __future__ import annotations

import pytest

from sidequest.agents.tool_registry import (
    ToolCategory,
    ToolContext,
    ToolResult,
    ToolResultStatus,
)


def test_tool_result_ok_payload() -> None:
    r = ToolResult.ok({"hp": 12})
    assert r.status is ToolResultStatus.OK
    assert r.payload == {"hp": 12}
    assert r.message is None


def test_tool_result_not_found_carries_message() -> None:
    r = ToolResult.not_found("no monster named 'banana'")
    assert r.status is ToolResultStatus.NOT_FOUND
    assert r.message == "no monster named 'banana'"


def test_tool_result_error_recoverable_default() -> None:
    r = ToolResult.error("validation failed")
    assert r.status is ToolResultStatus.ERROR_RECOVERABLE
    assert r.message == "validation failed"


def test_tool_result_error_non_recoverable() -> None:
    r = ToolResult.error("db corrupt", recoverable=False)
    assert r.status is ToolResultStatus.ERROR_FATAL


def test_tool_result_to_anthropic_payload_ok() -> None:
    r = ToolResult.ok({"x": 1})
    body, is_error = r.to_anthropic_payload()
    assert is_error is False
    assert '"x"' in body


def test_tool_result_to_anthropic_payload_error_recoverable() -> None:
    r = ToolResult.error("nope")
    body, is_error = r.to_anthropic_payload()
    assert is_error is True
    assert "nope" in body


def test_tool_category_enum_values() -> None:
    assert ToolCategory.READ.value == "read"
    assert ToolCategory.WRITE.value == "write"
    assert ToolCategory.GENERATE.value == "generate"


def test_tool_context_is_frozen() -> None:
    from unittest.mock import MagicMock

    ctx = ToolContext(
        world_id="w",
        session_id="s",
        perspective_pc="alex",
        turn_number=42,
        store=MagicMock(),
        otel_span=MagicMock(),
        perception_filter=MagicMock(),
    )
    with pytest.raises(Exception):
        ctx.world_id = "different"  # type: ignore[misc]


def test_tool_context_perspective_pc_optional() -> None:
    from unittest.mock import MagicMock

    ctx = ToolContext(
        world_id="w",
        session_id="s",
        perspective_pc=None,
        turn_number=1,
        store=MagicMock(),
        otel_span=MagicMock(),
        perception_filter=MagicMock(),
    )
    assert ctx.perspective_pc is None
```

- [ ] **Step 1.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_tool_registry.py -v
```

Expected: ImportError.

- [ ] **Step 1.3: Implement the primitives**

Create `sidequest-server/sidequest/agents/tool_registry.py`:
```python
"""Tool registry — Phase B foundation.

@tool decorator + ToolContext + ToolResult + Registry + dispatch.
Phase C populates the v1 catalog by importing each adapter from
sidequest.agents.tools.<name>.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from sidequest.agents.perception_filter import PerceptionFilter


class ToolCategory(str, Enum):
    READ = "read"
    WRITE = "write"
    GENERATE = "generate"


class ToolResultStatus(str, Enum):
    OK = "ok"
    NOT_FOUND = "not_found"
    ERROR_RECOVERABLE = "error_recoverable"
    ERROR_FATAL = "error_fatal"


@dataclass(frozen=True, slots=True)
class ToolResult:
    status: ToolResultStatus
    payload: Any | None = None
    message: str | None = None

    @classmethod
    def ok(cls, payload: Any) -> "ToolResult":
        return cls(status=ToolResultStatus.OK, payload=payload)

    @classmethod
    def not_found(cls, message: str) -> "ToolResult":
        return cls(status=ToolResultStatus.NOT_FOUND, message=message)

    @classmethod
    def error(cls, message: str, *, recoverable: bool = True) -> "ToolResult":
        status = (
            ToolResultStatus.ERROR_RECOVERABLE
            if recoverable
            else ToolResultStatus.ERROR_FATAL
        )
        return cls(status=status, message=message)

    def to_anthropic_payload(self) -> tuple[str, bool]:
        """Render as (content_str, is_error) for the SDK tool_result message."""
        if self.status is ToolResultStatus.OK:
            return (json.dumps(self.payload, default=str), False)
        if self.status is ToolResultStatus.NOT_FOUND:
            return (f"NOT_FOUND: {self.message}", False)
        # error_recoverable / error_fatal
        return (f"ERROR: {self.message}", True)


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Runtime state injected into each tool handler.

    The model never sees ToolContext — it is the server-side companion to
    the JSON-Schema-validated args the model does see.
    """

    world_id: str
    session_id: str
    perspective_pc: str | None
    turn_number: int
    store: Any  # SqliteStore — kept Any to avoid Phase B coupling
    otel_span: "Span"
    perception_filter: "PerceptionFilter"
```

- [ ] **Step 1.4: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_tool_registry.py -v
```

Expected: 9 passed.

- [ ] **Step 1.5: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/tool_registry.py tests/agents/test_tool_registry.py
uv run pyright sidequest/agents/tool_registry.py tests/agents/test_tool_registry.py
```

Expected: no findings.

- [ ] **Step 1.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/tool_registry.py tests/agents/test_tool_registry.py
git commit -m "feat(agents): add ToolContext + ToolResult primitives

Phase B foundation. Pure dataclass + enum primitives. ToolResult has
three constructors (ok / not_found / error) plus a to_anthropic_payload
method that renders to the SDK tool_result content string + is_error bool."
```

---

## Task 2 — `PerceptionFilter` primitive

**Files:**
- Create: `sidequest-server/sidequest/agents/perception_filter.py`
- Test: `sidequest-server/tests/agents/test_perception_filter.py`

Defines the Protocol; ships a `NoopPerceptionFilter` default. Per-tool filter rules (from spec §Perception filtering) land in Phase C alongside each tool conversion.

- [ ] **Step 2.1: Write the failing test**

Create `sidequest-server/tests/agents/test_perception_filter.py`:
```python
"""Tests for PerceptionFilter Protocol + Noop default."""

from __future__ import annotations

from sidequest.agents.perception_filter import (
    NoopPerceptionFilter,
    PerceptionFilter,
)
from sidequest.agents.tool_registry import ToolCategory, ToolResult


def test_noop_perception_filter_passes_payload_through() -> None:
    f = NoopPerceptionFilter()
    result = ToolResult.ok({"hp": 17})
    filtered = f.filter_result(
        tool_name="query_character",
        category=ToolCategory.READ,
        result=result,
        perspective_pc="alex",
    )
    assert filtered.payload == {"hp": 17}


def test_noop_perception_filter_passes_through_when_pc_none() -> None:
    f = NoopPerceptionFilter()
    result = ToolResult.ok({"hp": 17})
    filtered = f.filter_result(
        tool_name="query_character",
        category=ToolCategory.READ,
        result=result,
        perspective_pc=None,
    )
    assert filtered.payload == {"hp": 17}


def test_noop_perception_filter_passes_through_not_found() -> None:
    f = NoopPerceptionFilter()
    result = ToolResult.not_found("no such monster")
    filtered = f.filter_result(
        tool_name="lookup_monster",
        category=ToolCategory.READ,
        result=result,
        perspective_pc="alex",
    )
    assert filtered.message == "no such monster"


def test_noop_perception_filter_passes_through_write_results() -> None:
    """Write tools' results carry mutation status; filter must not redact them."""
    f = NoopPerceptionFilter()
    result = ToolResult.ok({"applied": True, "new_hp": 5})
    filtered = f.filter_result(
        tool_name="apply_damage",
        category=ToolCategory.WRITE,
        result=result,
        perspective_pc="alex",
    )
    assert filtered.payload == {"applied": True, "new_hp": 5}


def test_noop_satisfies_protocol() -> None:
    f = NoopPerceptionFilter()
    assert isinstance(f, PerceptionFilter)
```

- [ ] **Step 2.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_perception_filter.py -v
```

Expected: ImportError.

- [ ] **Step 2.3: Implement perception_filter**

Create `sidequest-server/sidequest/agents/perception_filter.py`:
```python
"""PerceptionFilter — Phase B primitive.

The narrator's tool path runs every tool result through a PerceptionFilter
before handing it back to the model. The Noop default passes everything
through unchanged; Phase C wires per-tool filter rules (see spec §Perception
filtering at the tool layer for the per-tool rule table).

Write tools' results are intentionally not redacted: mutation status must
be objectively reported. The filter inspects category to decide whether
redaction is in scope.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sidequest.agents.tool_registry import ToolCategory, ToolResult


@runtime_checkable
class PerceptionFilter(Protocol):
    def filter_result(
        self,
        *,
        tool_name: str,
        category: ToolCategory,
        result: ToolResult,
        perspective_pc: str | None,
    ) -> ToolResult: ...


class NoopPerceptionFilter:
    """Default — pass through. Use in tests + Phase B integration."""

    def filter_result(
        self,
        *,
        tool_name: str,
        category: ToolCategory,
        result: ToolResult,
        perspective_pc: str | None,
    ) -> ToolResult:
        return result
```

- [ ] **Step 2.4: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_perception_filter.py -v
```

Expected: 5 passed.

- [ ] **Step 2.5: Lint + type-check**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/perception_filter.py tests/agents/test_perception_filter.py
uv run pyright sidequest/agents/perception_filter.py tests/agents/test_perception_filter.py
```

Expected: no findings.

- [ ] **Step 2.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/perception_filter.py tests/agents/test_perception_filter.py
git commit -m "feat(agents): add PerceptionFilter primitive + Noop default

Phase B foundation. Replaces ADR-028's post-pass rewriter approach with
a server-side filter on tool results. Noop default passes everything
through; per-tool filter rules land in Phase C with each tool conversion."
```

---

## Task 3 — `tool_dispatch` OTEL span

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/tool_dispatch.py`
- Test: `sidequest-server/tests/telemetry/test_tool_dispatch_span.py`

- [ ] **Step 3.1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_tool_dispatch_span.py`:
```python
"""Tests for the tool.{category}.{name} OTEL span."""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.agents.tool_registry import ToolCategory
from sidequest.telemetry.spans.tool_dispatch import tool_dispatch_span


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    trace.set_tracer_provider(provider)
    return exp


def test_read_span_name(exporter: InMemorySpanExporter) -> None:
    with tool_dispatch_span(name="query_npc", category=ToolCategory.READ):
        pass
    assert exporter.get_finished_spans()[0].name == "tool.read.query_npc"


def test_write_span_name(exporter: InMemorySpanExporter) -> None:
    with tool_dispatch_span(name="apply_damage", category=ToolCategory.WRITE):
        pass
    assert exporter.get_finished_spans()[0].name == "tool.write.apply_damage"


def test_generate_span_name(exporter: InMemorySpanExporter) -> None:
    with tool_dispatch_span(name="roll_dice", category=ToolCategory.GENERATE):
        pass
    assert exporter.get_finished_spans()[0].name == "tool.gen.roll_dice"


def test_seed_attributes(exporter: InMemorySpanExporter) -> None:
    with tool_dispatch_span(
        name="query_npc",
        category=ToolCategory.READ,
        perspective_pc="alex",
    ) as span:
        span.set_attribute("tool.npc.name", "innkeeper")
    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs["tool.name"] == "query_npc"
    assert attrs["tool.category"] == "read"
    assert attrs["tool.perspective_pc"] == "alex"
    assert attrs["tool.npc.name"] == "innkeeper"


def test_records_exception(exporter: InMemorySpanExporter) -> None:
    with pytest.raises(RuntimeError):
        with tool_dispatch_span(name="x", category=ToolCategory.READ):
            raise RuntimeError("boom")
    span = exporter.get_finished_spans()[0]
    assert span.status.status_code.name == "ERROR"
```

- [ ] **Step 3.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/telemetry/test_tool_dispatch_span.py -v
```

Expected: ImportError.

- [ ] **Step 3.3: Implement the span module**

Create `sidequest-server/sidequest/telemetry/spans/tool_dispatch.py`:
```python
"""OTEL span: tool.{read,write,gen}.{name} — one span per tool handler call.

Standard attributes (set by dispatcher):
    tool.name              str
    tool.category          "read" | "write" | "generate"
    tool.perspective_pc    str | None
    tool.result_status     "ok" | "not_found" | "error_recoverable" | "error_fatal"
    tool.result_size_bytes int
    tool.duration_ms       float (recorded by span itself via start/end times)

Per-tool typed attributes use `tool.<short_name>.*` namespace (e.g.
`tool.npc.name`, `tool.damage.hp_delta`). Phase C tools set their own.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from sidequest.agents.tool_registry import ToolCategory

_TRACER = trace.get_tracer(__name__)

_CATEGORY_PREFIX: dict[ToolCategory, str] = {
    ToolCategory.READ: "tool.read",
    ToolCategory.WRITE: "tool.write",
    ToolCategory.GENERATE: "tool.gen",
}


@contextmanager
def tool_dispatch_span(
    *,
    name: str,
    category: ToolCategory,
    perspective_pc: str | None = None,
) -> Iterator[Span]:
    span_name = f"{_CATEGORY_PREFIX[category]}.{name}"
    with _TRACER.start_as_current_span(span_name) as span:
        span.set_attribute("tool.name", name)
        span.set_attribute("tool.category", category.value)
        if perspective_pc is not None:
            span.set_attribute("tool.perspective_pc", perspective_pc)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
```

- [ ] **Step 3.4: Run the test to verify it passes**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/telemetry/test_tool_dispatch_span.py -v
```

Expected: 5 passed.

- [ ] **Step 3.5: Lint + type-check + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/telemetry/spans/tool_dispatch.py tests/telemetry/test_tool_dispatch_span.py
uv run pyright sidequest/telemetry/spans/tool_dispatch.py tests/telemetry/test_tool_dispatch_span.py
git add sidequest/telemetry/spans/tool_dispatch.py tests/telemetry/test_tool_dispatch_span.py
git commit -m "feat(telemetry): add tool.{cat}.{name} OTEL span"
```

---

## Task 4 — `@tool` decorator + Registry class

**Files:**
- Modify: `sidequest-server/sidequest/agents/tool_registry.py` (add decorator + Registry)
- Modify: `sidequest-server/tests/agents/test_tool_registry.py` (extend)
- Create: `sidequest-server/sidequest/agents/tools/__init__.py`

- [ ] **Step 4.1: Create the tools barrel**

Create `sidequest-server/sidequest/agents/tools/__init__.py`:
```python
"""Tool adapters — Phase C populates this package.

Each adapter module calls @tool at import time. This barrel imports each
adapter so the registry is loaded by importing this package.
"""

# Phase C will add lines like:
#   from sidequest.agents.tools import lookup_monster  # noqa: F401
# one per adapter, here.
```

- [ ] **Step 4.2: Extend the registry test**

Append to `sidequest-server/tests/agents/test_tool_registry.py`:
```python
import asyncio
from typing import Any
from unittest.mock import MagicMock

from pydantic import BaseModel, Field

from sidequest.agents.tool_registry import Registry, tool


def _make_ctx() -> ToolContext:
    return ToolContext(
        world_id="w",
        session_id="s",
        perspective_pc="alex",
        turn_number=1,
        store=MagicMock(),
        otel_span=MagicMock(),
        perception_filter=_NoopFilter(),
    )


class _NoopFilter:
    def filter_result(
        self, *, tool_name: str, category: ToolCategory, result: ToolResult, perspective_pc: str | None
    ) -> ToolResult:
        return result


class _SidesArgs(BaseModel):
    sides: int = Field(..., gt=0)


class _NoArgs(BaseModel):
    pass


async def test_registry_registers_and_lists_tools() -> None:
    reg = Registry()

    @tool(name="echo", description="echo", category=ToolCategory.READ, registry=reg)
    async def echo(args: _NoArgs, ctx: ToolContext) -> ToolResult:
        return ToolResult.ok({})

    assert "echo" in reg.list_names()
    defs = reg.tool_definitions()
    assert any(d.name == "echo" for d in defs)


async def test_registry_dispatch_runs_handler() -> None:
    reg = Registry()

    @tool(name="roll", description="roll", category=ToolCategory.GENERATE, registry=reg)
    async def roll(args: _SidesArgs, ctx: ToolContext) -> ToolResult:
        return ToolResult.ok({"value": args.sides // 2})

    from sidequest.agents.tooling_protocol import ToolUseBlock

    out = await reg.dispatch(
        ToolUseBlock(id="t1", name="roll", arguments={"sides": 20}),
        _make_ctx(),
    )
    assert out.tool_use_id == "t1"
    assert "10" in out.content
    assert out.is_error is False


async def test_registry_dispatch_returns_error_for_unknown_tool() -> None:
    reg = Registry()
    from sidequest.agents.tooling_protocol import ToolUseBlock

    out = await reg.dispatch(
        ToolUseBlock(id="t1", name="nope", arguments={}),
        _make_ctx(),
    )
    assert out.is_error is True
    assert "unknown tool" in out.content.lower()


async def test_registry_dispatch_rejects_bad_args() -> None:
    reg = Registry()

    @tool(name="roll", description="roll", category=ToolCategory.GENERATE, registry=reg)
    async def roll(args: _SidesArgs, ctx: ToolContext) -> ToolResult:
        return ToolResult.ok({})

    from sidequest.agents.tooling_protocol import ToolUseBlock

    out = await reg.dispatch(
        ToolUseBlock(id="t1", name="roll", arguments={"sides": -1}),
        _make_ctx(),
    )
    assert out.is_error is True


async def test_registry_dispatch_serializes_writes_per_session() -> None:
    """Two parallel writes against one session run sequentially."""
    reg = Registry()
    order: list[str] = []

    @tool(name="write_a", description="a", category=ToolCategory.WRITE, registry=reg)
    async def w_a(args: _NoArgs, ctx: ToolContext) -> ToolResult:
        order.append("a-start")
        await asyncio.sleep(0.02)
        order.append("a-end")
        return ToolResult.ok({})

    @tool(name="write_b", description="b", category=ToolCategory.WRITE, registry=reg)
    async def w_b(args: _NoArgs, ctx: ToolContext) -> ToolResult:
        order.append("b-start")
        await asyncio.sleep(0.02)
        order.append("b-end")
        return ToolResult.ok({})

    from sidequest.agents.tooling_protocol import ToolUseBlock

    ctx = _make_ctx()
    await asyncio.gather(
        reg.dispatch(ToolUseBlock(id="1", name="write_a", arguments={}), ctx),
        reg.dispatch(ToolUseBlock(id="2", name="write_b", arguments={}), ctx),
    )
    # Sequential: a fully runs before b starts, or vice-versa.
    assert order in (
        ["a-start", "a-end", "b-start", "b-end"],
        ["b-start", "b-end", "a-start", "a-end"],
    )


async def test_registry_dispatch_parallelises_reads() -> None:
    """Reads on the same session may overlap."""
    reg = Registry()
    overlap = {"a_running": False, "b_saw_a": False}

    @tool(name="read_a", description="a", category=ToolCategory.READ, registry=reg)
    async def r_a(args: _NoArgs, ctx: ToolContext) -> ToolResult:
        overlap["a_running"] = True
        await asyncio.sleep(0.02)
        overlap["a_running"] = False
        return ToolResult.ok({})

    @tool(name="read_b", description="b", category=ToolCategory.READ, registry=reg)
    async def r_b(args: _NoArgs, ctx: ToolContext) -> ToolResult:
        if overlap["a_running"]:
            overlap["b_saw_a"] = True
        return ToolResult.ok({})

    from sidequest.agents.tooling_protocol import ToolUseBlock

    ctx = _make_ctx()
    await asyncio.gather(
        reg.dispatch(ToolUseBlock(id="1", name="read_a", arguments={}), ctx),
        asyncio.sleep(0.01),
    )
    # Confirm parallel-ability via direct overlap check.
    async def fire_pair() -> None:
        await asyncio.gather(
            reg.dispatch(ToolUseBlock(id="1", name="read_a", arguments={}), ctx),
            reg.dispatch(ToolUseBlock(id="2", name="read_b", arguments={}), ctx),
        )
    await fire_pair()
    assert overlap["b_saw_a"] is True


async def test_registry_dispatch_invokes_perception_filter() -> None:
    reg = Registry()
    seen: list[str] = []

    class _Tracking:
        def filter_result(
            self, *, tool_name: str, category: ToolCategory, result: ToolResult, perspective_pc: str | None
        ) -> ToolResult:
            seen.append(tool_name)
            return result

    @tool(name="q", description="q", category=ToolCategory.READ, registry=reg)
    async def q(args: _NoArgs, ctx: ToolContext) -> ToolResult:
        return ToolResult.ok({"x": 1})

    from sidequest.agents.tooling_protocol import ToolUseBlock

    ctx = ToolContext(
        world_id="w",
        session_id="s",
        perspective_pc="alex",
        turn_number=1,
        store=MagicMock(),
        otel_span=MagicMock(),
        perception_filter=_Tracking(),
    )
    await reg.dispatch(ToolUseBlock(id="t", name="q", arguments={}), ctx)
    assert seen == ["q"]
```

- [ ] **Step 4.3: Run the failing tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_tool_registry.py -v
```

Expected: import / attribute errors for `Registry`, `tool`.

- [ ] **Step 4.4: Implement the decorator + Registry**

Append to `sidequest-server/sidequest/agents/tool_registry.py`:
```python
import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from sidequest.agents.tooling_protocol import (
    ToolDefinition,
    ToolResultBlock,
    ToolUseBlock,
)
from sidequest.telemetry.spans.tool_dispatch import tool_dispatch_span

_ArgsT = TypeVar("_ArgsT", bound=BaseModel)
ToolHandler = Callable[[_ArgsT, ToolContext], Awaitable[ToolResult]]


@dataclass(frozen=True, slots=True)
class _RegisteredTool:
    name: str
    description: str
    category: ToolCategory
    args_model: type[BaseModel]
    handler: Callable[..., Awaitable[ToolResult]]


class Registry:
    """Holds the @tool-decorated handlers and dispatches tool_use blocks."""

    def __init__(self) -> None:
        self._tools: dict[str, _RegisteredTool] = {}
        self._write_locks: dict[str, asyncio.Lock] = {}

    def register(
        self,
        *,
        name: str,
        description: str,
        category: ToolCategory,
        args_model: type[BaseModel],
        handler: Callable[..., Awaitable[ToolResult]],
    ) -> None:
        if name in self._tools:
            raise ValueError(f"Tool {name!r} already registered")
        self._tools[name] = _RegisteredTool(
            name=name,
            description=description,
            category=category,
            args_model=args_model,
            handler=handler,
        )

    def list_names(self) -> list[str]:
        return sorted(self._tools)

    def tool_definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name=t.name,
                description=t.description,
                input_schema=t.args_model.model_json_schema(),
            )
            for t in self._tools.values()
        ]

    async def dispatch(
        self,
        block: ToolUseBlock,
        ctx: ToolContext,
    ) -> ToolResultBlock:
        registered = self._tools.get(block.name)
        if registered is None:
            err = ToolResult.error(
                f"unknown tool {block.name!r}",
                recoverable=True,
            )
            body, is_err = err.to_anthropic_payload()
            return ToolResultBlock(tool_use_id=block.id, content=body, is_error=is_err)

        with tool_dispatch_span(
            name=registered.name,
            category=registered.category,
            perspective_pc=ctx.perspective_pc,
        ) as span:
            try:
                args = registered.args_model.model_validate(block.arguments)
            except ValidationError as exc:
                err = ToolResult.error(
                    f"argument validation failed: {exc.errors()}",
                    recoverable=True,
                )
                body, is_err = err.to_anthropic_payload()
                span.set_attribute("tool.result_status", err.status.value)
                span.set_attribute("tool.result_size_bytes", len(body))
                return ToolResultBlock(
                    tool_use_id=block.id, content=body, is_error=is_err
                )

            if registered.category is ToolCategory.WRITE:
                lock = self._write_locks.setdefault(ctx.session_id, asyncio.Lock())
                async with lock:
                    result = await registered.handler(args, ctx)
            else:
                result = await registered.handler(args, ctx)

            filtered = ctx.perception_filter.filter_result(
                tool_name=registered.name,
                category=registered.category,
                result=result,
                perspective_pc=ctx.perspective_pc,
            )

            body, is_err = filtered.to_anthropic_payload()
            span.set_attribute("tool.result_status", filtered.status.value)
            span.set_attribute("tool.result_size_bytes", len(body))
            return ToolResultBlock(
                tool_use_id=block.id, content=body, is_error=is_err
            )


# ----------------------------------------------------------------------
# Module-level default registry + decorator
# ----------------------------------------------------------------------

default_registry = Registry()


def tool(
    *,
    name: str,
    description: str,
    category: ToolCategory,
    registry: Registry | None = None,
):
    """Decorator: register an async handler with a Pydantic-args model."""
    chosen = registry if registry is not None else default_registry

    def decorate(fn: Callable[..., Awaitable[ToolResult]]) -> Callable[..., Awaitable[ToolResult]]:
        import inspect

        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        if not params:
            raise TypeError(
                f"@tool {name!r} handler must take (args_model, ctx) — got no params"
            )
        args_annotation = params[0].annotation
        if (
            args_annotation is inspect.Parameter.empty
            or not isinstance(args_annotation, type)
            or not issubclass(args_annotation, BaseModel)
        ):
            raise TypeError(
                f"@tool {name!r}: first parameter must be annotated with a pydantic.BaseModel subclass"
            )
        chosen.register(
            name=name,
            description=description,
            category=category,
            args_model=args_annotation,
            handler=fn,
        )
        return fn

    return decorate
```

- [ ] **Step 4.5: Run all registry tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_tool_registry.py -v
```

Expected: all tests pass.

- [ ] **Step 4.6: Lint + type-check + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/tool_registry.py tests/agents/test_tool_registry.py sidequest/agents/tools/__init__.py
uv run pyright sidequest/agents/tool_registry.py tests/agents/test_tool_registry.py
git add sidequest/agents/tool_registry.py tests/agents/test_tool_registry.py sidequest/agents/tools/__init__.py
git commit -m "feat(agents): add @tool decorator + Registry + dispatch

Phase B foundation. @tool registers at import time; Registry.dispatch
validates args, opens a tool.{cat}.{name} OTEL span, serializes writes
per session, parallelizes reads/generates, and routes results through
the PerceptionFilter. Phase C populates the v1 catalog via the
sidequest.agents.tools package."
```

---

## Task 5 — Wiring test: registry + SDK client + tool round-trip

**Files:**
- Create: `sidequest-server/tests/agents/test_tool_registry_wiring.py`

End-to-end: a registered tool + an `AnthropicSdkClient` injected with a fake SDK + a scripted two-step (tool_use → end_turn) flow. Verifies the dispatch round-trip is wired into the client.

- [ ] **Step 5.1: Write the wiring test**

Create `sidequest-server/tests/agents/test_tool_registry_wiring.py`:
```python
"""Phase B wiring test — registry + SDK client + dispatch round-trip."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from sidequest.agents.anthropic_sdk_client import AnthropicSdkClient
from sidequest.agents.perception_filter import NoopPerceptionFilter
from sidequest.agents.tool_registry import (
    Registry,
    ToolCategory,
    ToolContext,
    ToolResult,
    tool,
)
from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
    ToolUseBlock,
)


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class _Text:
    type: str
    text: str


@dataclass
class _ToolUse:
    type: str
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class _Resp:
    content: list[Any]
    stop_reason: str
    usage: _Usage
    model: str


class _Msgs:
    def __init__(self, responses: list[_Resp]) -> None:
        self._r = responses
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> _Resp:
        self.calls.append(kwargs)
        return self._r.pop(0)


class _Sdk:
    def __init__(self, responses: list[_Resp]) -> None:
        self.messages = _Msgs(responses)


class _DiceArgs(BaseModel):
    sides: int = Field(..., gt=0)


async def test_registry_round_trip_via_sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    reg = Registry()

    @tool(name="roll_dice", description="Roll dice.", category=ToolCategory.GENERATE, registry=reg)
    async def roll(args: _DiceArgs, ctx: ToolContext) -> ToolResult:
        return ToolResult.ok({"value": args.sides})

    sdk = _Sdk(
        responses=[
            _Resp(
                content=[
                    _ToolUse(type="tool_use", id="t1", name="roll_dice", input={"sides": 20})
                ],
                stop_reason="tool_use",
                usage=_Usage(input_tokens=200, output_tokens=15),
                model="claude-sonnet-4-6",
            ),
            _Resp(
                content=[_Text(type="text", text="A natural 20.")],
                stop_reason="end_turn",
                usage=_Usage(input_tokens=220, output_tokens=10),
                model="claude-sonnet-4-6",
            ),
        ]
    )
    client = AnthropicSdkClient(sdk=sdk)
    ctx = ToolContext(
        world_id="w",
        session_id="s",
        perspective_pc="alex",
        turn_number=1,
        store=MagicMock(),
        otel_span=MagicMock(),
        perception_filter=NoopPerceptionFilter(),
    )

    def dispatch(block: ToolUseBlock):
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(reg.dispatch(block, ctx))

    # The SDK client uses a *sync* tool_dispatch callback. We capture via a
    # one-shot helper that runs the registry's async dispatch on the current
    # loop using `asyncio.run_coroutine_threadsafe`-style invocation. For
    # the integration test, simpler: drive the registry inline through a
    # synchronous adapter that awaits via nest_asyncio is overkill — use
    # the registry's dispatch directly in a coroutine and pass a closure.

    import asyncio
    captured: dict[str, Any] = {}

    async def run() -> None:
        sync_results: list[Any] = []

        def sync_dispatch(block: ToolUseBlock):
            # Schedule the async dispatch on the same loop and block.
            fut = asyncio.ensure_future(reg.dispatch(block, ctx))
            return asyncio.get_event_loop().run_until_complete(fut)

        # We can't reenter the loop, so swap to direct awaiting inline.
        # The SDK client's tool_dispatch param is sync in Phase A; for Phase B
        # we adapt by precomputing results before passing.
        # Instead: use the loop-friendly approach — pre-dispatch in a wrapper.
        from sidequest.agents.tooling_protocol import ToolResultBlock

        def sync_dispatch_inline(block: ToolUseBlock) -> ToolResultBlock:
            return asyncio.get_event_loop().run_until_complete(reg.dispatch(block, ctx))

        result = await client.complete_with_tools(
            system_blocks=[CacheableBlock(text="rules", cache=True)],
            messages=[Message(role="user", content="roll d20")],
            tools=reg.tool_definitions(),
            tool_dispatch=sync_dispatch_inline,
            model="claude-sonnet-4-6",
        )
        captured["result"] = result

    # Real run.
    import asyncio as _aio

    asyncio.run(run())
    res = captured["result"]
    assert res.text == "A natural 20."
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "roll_dice"
```

> **Adapter note:** Phase A's SDK client uses a synchronous `tool_dispatch` callback. To call the async registry from a sync callback we'd need `nest_asyncio` or a redesign. The cleaner fix is to widen `tool_dispatch` to accept `Awaitable[ToolResultBlock]` — defer to Step 5.2 below.

- [ ] **Step 5.2: Widen `tool_dispatch` to accept async**

Edit `sidequest-server/sidequest/agents/anthropic_sdk_client.py`. Change the `tool_dispatch` parameter type and the call site:

In the method signature, change:
```python
        tool_dispatch: Callable[[ToolUseBlock], ToolResultBlock] | None = None,
```
to:
```python
        tool_dispatch: Callable[[ToolUseBlock], Awaitable[ToolResultBlock]] | Callable[[ToolUseBlock], ToolResultBlock] | None = None,
```

Add at top of file:
```python
import inspect
from collections.abc import Awaitable
```

In the body where `result = tool_dispatch(tu)` is called, change to:
```python
                maybe = tool_dispatch(tu)
                if inspect.isawaitable(maybe):
                    result = await maybe
                else:
                    result = maybe
```

Update `sidequest-server/sidequest/agents/tooling_protocol.py` `ToolingLlmClient` Protocol signature in the same way (widen `tool_dispatch` to accept the async form).

- [ ] **Step 5.3: Simplify the wiring test**

Replace `tests/agents/test_tool_registry_wiring.py` body with a clean async dispatch:
```python
"""Phase B wiring test — registry + SDK client + dispatch round-trip."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from sidequest.agents.anthropic_sdk_client import AnthropicSdkClient
from sidequest.agents.perception_filter import NoopPerceptionFilter
from sidequest.agents.tool_registry import (
    Registry,
    ToolCategory,
    ToolContext,
    ToolResult,
    tool,
)
from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
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
class _Text:
    type: str
    text: str


@dataclass
class _ToolUse:
    type: str
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class _Resp:
    content: list[Any]
    stop_reason: str
    usage: _Usage
    model: str


class _Msgs:
    def __init__(self, responses: list[_Resp]) -> None:
        self._r = responses
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> _Resp:
        self.calls.append(kwargs)
        return self._r.pop(0)


class _Sdk:
    def __init__(self, responses: list[_Resp]) -> None:
        self.messages = _Msgs(responses)


class _DiceArgs(BaseModel):
    sides: int = Field(..., gt=0)


async def test_registry_round_trip_via_sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    reg = Registry()

    @tool(
        name="roll_dice",
        description="Roll dice.",
        category=ToolCategory.GENERATE,
        registry=reg,
    )
    async def roll(args: _DiceArgs, ctx: ToolContext) -> ToolResult:
        return ToolResult.ok({"value": args.sides})

    sdk = _Sdk(
        responses=[
            _Resp(
                content=[
                    _ToolUse(
                        type="tool_use",
                        id="t1",
                        name="roll_dice",
                        input={"sides": 20},
                    )
                ],
                stop_reason="tool_use",
                usage=_Usage(input_tokens=200, output_tokens=15),
                model="claude-sonnet-4-6",
            ),
            _Resp(
                content=[_Text(type="text", text="A natural 20.")],
                stop_reason="end_turn",
                usage=_Usage(input_tokens=220, output_tokens=10),
                model="claude-sonnet-4-6",
            ),
        ]
    )
    client = AnthropicSdkClient(sdk=sdk)
    ctx = ToolContext(
        world_id="w",
        session_id="s",
        perspective_pc="alex",
        turn_number=1,
        store=MagicMock(),
        otel_span=MagicMock(),
        perception_filter=NoopPerceptionFilter(),
    )

    async def dispatch(block: ToolUseBlock) -> ToolResultBlock:
        return await reg.dispatch(block, ctx)

    result = await client.complete_with_tools(
        system_blocks=[CacheableBlock(text="rules", cache=True)],
        messages=[Message(role="user", content="roll d20")],
        tools=reg.tool_definitions(),
        tool_dispatch=dispatch,
        model="claude-sonnet-4-6",
    )
    assert result.text == "A natural 20."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "roll_dice"
```

- [ ] **Step 5.4: Run the wiring test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_tool_registry_wiring.py -v
```

Expected: 1 passed.

- [ ] **Step 5.5: Re-run Phase A tests to confirm tool_dispatch widening didn't regress**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client_wiring.py tests/agents/test_fake_anthropic_sdk_client.py -v
```

Expected: all pass.

- [ ] **Step 5.6: Update `FakeAnthropicSdkClient` to mirror the widened protocol**

In `tests/agents/fakes/fake_anthropic_sdk_client.py`, mirror the same widening: accept either sync or async `tool_dispatch`, await if awaitable.

In `complete_with_tools`, replace the call:
```python
                results.append(tool_dispatch(tu))
```
with:
```python
                import inspect as _inspect
                maybe = tool_dispatch(tu)
                if _inspect.isawaitable(maybe):
                    results.append(await maybe)
                else:
                    results.append(maybe)
```

Update the signature:
```python
        tool_dispatch: Callable[[ToolUseBlock], "ToolResultBlock | Awaitable[ToolResultBlock]"] | None = None,
```

- [ ] **Step 5.7: Re-run the full Phase A fake tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_fake_anthropic_sdk_client.py -v
```

Expected: all pass.

- [ ] **Step 5.8: Lint + type-check + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/agents/ tests/agents/
uv run pyright sidequest/agents/ tests/agents/
git add sidequest/agents/anthropic_sdk_client.py sidequest/agents/tooling_protocol.py tests/agents/fakes/fake_anthropic_sdk_client.py tests/agents/test_tool_registry_wiring.py
git commit -m "feat(agents): widen tool_dispatch to accept async + registry wiring test

Phase B wiring. tool_dispatch in ToolingLlmClient + AnthropicSdkClient +
FakeAnthropicSdkClient now accepts either sync or async callbacks. The
async path is what production wants (Registry.dispatch is async); sync
preserved for tests that don't need it. Plus the end-to-end wiring test:
SDK client + Registry + tool round-trip + perception filter."
```

---

## Task 6 — Export Phase B symbols + cleanup

**Files:**
- Modify: `sidequest-server/sidequest/agents/__init__.py`
- Modify: `sidequest-server/tests/agents/test_agents_exports.py`

- [ ] **Step 6.1: Extend the export test**

Append:
```python
def test_phase_b_registry_exports() -> None:
    from sidequest.agents import (
        NoopPerceptionFilter,
        PerceptionFilter,
        Registry,
        ToolCategory,
        ToolContext,
        ToolResult,
        ToolResultStatus,
        default_registry,
        tool,
    )
    assert Registry is not None
    assert tool is not None
    assert default_registry is not None
    assert PerceptionFilter is not None
    assert NoopPerceptionFilter is not None
```

- [ ] **Step 6.2: Run the failing test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_agents_exports.py -v
```

- [ ] **Step 6.3: Add exports**

Append to `sidequest-server/sidequest/agents/__init__.py`:
```python
from sidequest.agents.perception_filter import NoopPerceptionFilter, PerceptionFilter
from sidequest.agents.tool_registry import (
    Registry,
    ToolCategory,
    ToolContext,
    ToolResult,
    ToolResultStatus,
    default_registry,
    tool,
)
```

- [ ] **Step 6.4: Run + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_agents_exports.py -v
uv run ruff check sidequest/agents/__init__.py
uv run pyright sidequest/agents/__init__.py
git add sidequest/agents/__init__.py tests/agents/test_agents_exports.py
git commit -m "feat(agents): export Phase B registry symbols"
```

---

## Task 7 — Phase B acceptance: full sweep + push

- [ ] **Step 7.1: Run the full server test suite**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v
```

Expected: 100% pass.

- [ ] **Step 7.2: Lint + format + type check sweep**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

- [ ] **Step 7.3: Orchestrator gate**

```bash
cd /Users/slabgorb/Projects/oq-1/
just check-all
```

- [ ] **Step 7.4: Push**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git push origin feat/anthropic-sdk-migration
```

---

## Phase B completion check

- [ ] **Registry has zero tools registered in production.** Verify:
  ```bash
  cd /Users/slabgorb/Projects/oq-1/sidequest-server
  uv run python -c "from sidequest.agents import default_registry; print(default_registry.list_names())"
  ```
  Expected: `[]` (Phase C will populate this).
- [ ] **Narrator still on `claude -p`.** No production code imports `Registry`, `tool_registry`, or `AnthropicSdkClient` from the narrator path yet.
- [ ] **All Phase A + Phase B tests pass.**
- [ ] **Branch pushed.** No PR opened.

---

## What's next

Phase C plan: `2026-05-15-anthropic-sdk-migration-phase-c-tool-conversions.md` — one template task + 26 per-tool deltas.
