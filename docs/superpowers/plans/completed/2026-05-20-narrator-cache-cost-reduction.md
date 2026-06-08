# Narrator Cache Cost Reduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive the narrator's per-turn cache write cost toward zero by giving the tools array an explicit 1h cache marker, and wire 5m/1h write-breakdown telemetry through OTEL so the next playtest's dashboard can verify the fix.

**Architecture:** Add `cache_control` to the last entry of `_build_tools_array` (inherits the existing `self.cache_ttl`). Extend `ToolingResult` and the SDK client's usage extraction to read `usage.cache_creation.ephemeral_5m_input_tokens` and `ephemeral_1h_input_tokens`. Surface both on the existing `narration.turn` OTEL span alongside a new `narration.turn.system_block_sizes_json` diagnostic. ADR-101 gets an inline amendment documenting the four-region cache layout.

**Tech Stack:** Python 3.14, anthropic-python SDK 0.102, FastAPI server, pytest + InMemorySpanExporter for OTEL assertions, uv for env management.

**Spec:** [`docs/superpowers/specs/2026-05-20-narrator-cache-cost-reduction-design.md`](../specs/2026-05-20-narrator-cache-cost-reduction-design.md)

---

## File Structure

| File | Role |
|------|------|
| `sidequest-server/sidequest/agents/tooling_protocol.py` | `ToolingResult` dataclass — add two breakdown fields |
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` | Add tools cache_control marker; read breakdown from usage |
| `sidequest-server/sidequest/agents/orchestrator.py` | Emit new span attributes (5m/1h + block_sizes_json) |
| `sidequest-server/tests/agents/test_anthropic_sdk_client.py` | New tests: tools marker, breakdown plumbing |
| `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py` | Extended assertions for new span attributes |
| `sidequest-server/tests/agents/fakes/fake_anthropic_sdk_client.py` | `ScriptedResponse` gains the two breakdown fields |
| `docs/adr/101-anthropic-sdk-as-narrator-backend.md` | Inline amendment: four-region cache layout |

**Why this decomposition:** Each task touches one or two related files with a clear test boundary. The dataclass shape (Task 1) is foundational and every later task depends on it. Production-code changes (Tasks 2-5) ride on the dataclass. Orchestrator wiring (Tasks 6-7) rides on the SDK client surface. ADR amendment (Task 8) closes the design loop. No file does double duty in one task.

---

## Setup

- [ ] **Branching preflight**

The orchestrator already has branch `feat/spec-narrator-cache-cost-reduction` from spec authoring. The server needs its own feature branch off develop.

```bash
# From /Users/slabgorb/Projects/oq-2
git -C sidequest-server status                              # verify clean
git -C sidequest-server checkout develop                    # ensure on base
git -C sidequest-server pull --ff-only                      # update base
git -C sidequest-server checkout -b feat/narrator-cache-cost-reduction
git -C sidequest-server branch --show-current              # confirm
```

Expected: prints `feat/narrator-cache-cost-reduction`.

---

### Task 1: Extend `ToolingResult` with 5m/1h breakdown fields

**Files:**
- Modify: `sidequest-server/sidequest/agents/tooling_protocol.py:60-74`
- Test: `sidequest-server/tests/agents/test_anthropic_sdk_client.py` (add new test below)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/agents/test_anthropic_sdk_client.py`:

```python
def test_tooling_result_has_ttl_breakdown_fields() -> None:
    """ToolingResult exposes per-TTL write breakdowns so the orchestrator
    can attribute 5m vs 1h cache writes onto narration.turn spans."""
    from sidequest.agents.tooling_protocol import ToolingResult

    result = ToolingResult(
        text="ok",
        stop_reason="end_turn",
        input_tokens=10,
        output_tokens=2,
        cached_input_read_tokens=0,
        cached_input_write_tokens=0,
        model="claude-sonnet-4-6",
        cached_input_write_5m_tokens=100,
        cached_input_write_1h_tokens=200,
    )
    assert result.cached_input_write_5m_tokens == 100
    assert result.cached_input_write_1h_tokens == 200


def test_tooling_result_breakdown_fields_default_to_zero() -> None:
    """Legacy test fixtures that construct ToolingResult by hand without
    the new fields keep working."""
    from sidequest.agents.tooling_protocol import ToolingResult

    result = ToolingResult(
        text="ok",
        stop_reason="end_turn",
        input_tokens=10,
        output_tokens=2,
        cached_input_read_tokens=0,
        cached_input_write_tokens=0,
        model="claude-sonnet-4-6",
    )
    assert result.cached_input_write_5m_tokens == 0
    assert result.cached_input_write_1h_tokens == 0
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd sidequest-server
uv run pytest tests/agents/test_anthropic_sdk_client.py::test_tooling_result_has_ttl_breakdown_fields tests/agents/test_anthropic_sdk_client.py::test_tooling_result_breakdown_fields_default_to_zero -v
```

Expected: FAIL with `TypeError: ToolingResult.__init__() got an unexpected keyword argument 'cached_input_write_5m_tokens'`.

- [ ] **Step 3: Add the fields**

In `sidequest-server/sidequest/agents/tooling_protocol.py`, replace the `ToolingResult` dataclass (lines 60-74) with:

```python
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
    # Sum of `compute_cost_usd` across every iteration of the tool-use
    # loop. Defaults to 0.0 so legacy test doubles that construct
    # ToolingResult by hand keep working — production paths populate it.
    cumulative_cost_usd: float = 0.0
    # Per-TTL breakdown of `cached_input_write_tokens` from
    # `usage.cache_creation.ephemeral_{5m,1h}_input_tokens`. Default to 0
    # for SDK-version drift (<0.51 didn't expose the breakdown) and for
    # legacy fixtures.
    cached_input_write_5m_tokens: int = 0
    cached_input_write_1h_tokens: int = 0
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
uv run pytest tests/agents/test_anthropic_sdk_client.py::test_tooling_result_has_ttl_breakdown_fields tests/agents/test_anthropic_sdk_client.py::test_tooling_result_breakdown_fields_default_to_zero -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/tooling_protocol.py tests/agents/test_anthropic_sdk_client.py
git commit -m "feat(tooling_protocol): add 5m/1h cache-write breakdown to ToolingResult"
```

---

### Task 2: Extend `ScriptedResponse` and test fakes with breakdown fields

**Files:**
- Modify: `sidequest-server/tests/agents/fakes/fake_anthropic_sdk_client.py` (`ScriptedResponse` dataclass)
- Modify: `sidequest-server/tests/agents/test_anthropic_sdk_client.py` (`_Usage` dataclass)
- Modify: `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py` (`_Usage` dataclass)

This is **plumbing only** — extends the test doubles so subsequent tests can script the breakdown values. No production code changes.

- [ ] **Step 1: Extend `ScriptedResponse`**

In `sidequest-server/tests/agents/fakes/fake_anthropic_sdk_client.py`, modify the `ScriptedResponse` dataclass (around line 30-40):

```python
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
    cached_input_write_5m_tokens: int = 0
    cached_input_write_1h_tokens: int = 0
```

Then in the same file, update the body of `complete_with_tools` where it constructs the final `ToolingResult` to pass the new fields through. Find the `ToolingResult(` constructor call inside `complete_with_tools` and add the two new keyword arguments using the last `response`'s values:

```python
return ToolingResult(
    text=response.text,
    stop_reason=response.stop_reason,
    input_tokens=response.input_tokens,
    output_tokens=response.output_tokens,
    cached_input_read_tokens=response.cached_input_read_tokens,
    cached_input_write_tokens=response.cached_input_write_tokens,
    model=response.model,
    tool_calls=list(all_tool_calls),
    cumulative_cost_usd=cumulative_cost_usd,
    cached_input_write_5m_tokens=response.cached_input_write_5m_tokens,
    cached_input_write_1h_tokens=response.cached_input_write_1h_tokens,
)
```

(If the existing call already uses keyword arguments, just add the two new lines. If positional, convert to keyword and add.)

- [ ] **Step 2: Extend both `_Usage` dataclasses**

In `sidequest-server/tests/agents/test_anthropic_sdk_client.py`, replace the `_Usage` dataclass (lines 89-94) with:

```python
@dataclass(frozen=True)
class _CacheCreation:
    ephemeral_5m_input_tokens: int = 0
    ephemeral_1h_input_tokens: int = 0


@dataclass(frozen=True)
class _Usage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_creation: _CacheCreation | None = None
```

In `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py`, replace the second `_Usage` dataclass (lines 118-123) with:

```python
@dataclass
class _CacheCreation:
    ephemeral_5m_input_tokens: int = 0
    ephemeral_1h_input_tokens: int = 0


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_creation: _CacheCreation | None = None
```

- [ ] **Step 3: Run full test suite to verify nothing broke**

```bash
cd sidequest-server
uv run pytest tests/agents/test_anthropic_sdk_client.py tests/agents/test_cache_ttl_prefix_and_otel.py tests/agents/test_fake_anthropic_sdk_client.py -v
```

Expected: ALL PASS — this task adds optional fields with defaults; no behavioral change.

- [ ] **Step 4: Commit**

```bash
git add tests/agents/fakes/fake_anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py tests/agents/test_cache_ttl_prefix_and_otel.py
git commit -m "test(fakes): add 5m/1h breakdown fields to ScriptedResponse and _Usage"
```

---

### Task 3: Read 5m/1h breakdown from `usage.cache_creation` in `complete_with_tools`

**Files:**
- Modify: `sidequest-server/sidequest/agents/anthropic_sdk_client.py:141-200` (usage extraction + ToolingResult return)
- Test: `sidequest-server/tests/agents/test_anthropic_sdk_client.py` (add new test below)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/agents/test_anthropic_sdk_client.py`:

```python
async def test_ttl_breakdown_flows_into_tooling_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """usage.cache_creation.ephemeral_{5m,1h}_input_tokens reach ToolingResult."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sdk_response = _SdkResponse(
        content=[_SdkContentTextBlock(type="text", text="ok")],
        stop_reason="end_turn",
        usage=_Usage(
            input_tokens=10,
            output_tokens=2,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=300,
            cache_creation=_CacheCreation(
                ephemeral_5m_input_tokens=100,
                ephemeral_1h_input_tokens=200,
            ),
        ),
        model="claude-sonnet-4-6",
    )
    fake = _FakeAsyncSdk(responses=[sdk_response])
    client = AnthropicSdkClient(sdk=fake)
    result = await client.complete_with_tools(
        system_blocks=[CacheableBlock(text="x", cache=True)],
        messages=[Message(role="user", content="hi")],
        tools=[],
        model="claude-sonnet-4-6",
    )
    assert result.cached_input_write_5m_tokens == 100
    assert result.cached_input_write_1h_tokens == 200
    # Aggregate stays unchanged.
    assert result.cached_input_write_tokens == 300


async def test_ttl_breakdown_defaults_zero_when_field_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK-version-drift case: older SDKs return no `cache_creation` object.
    The breakdown silently goes to 0; the aggregate field stays correct."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sdk_response = _SdkResponse(
        content=[_SdkContentTextBlock(type="text", text="ok")],
        stop_reason="end_turn",
        usage=_Usage(
            input_tokens=10,
            output_tokens=2,
            cache_creation_input_tokens=500,
            cache_creation=None,  # older SDK shape
        ),
        model="claude-sonnet-4-6",
    )
    fake = _FakeAsyncSdk(responses=[sdk_response])
    client = AnthropicSdkClient(sdk=fake)
    result = await client.complete_with_tools(
        system_blocks=[CacheableBlock(text="x", cache=True)],
        messages=[Message(role="user", content="hi")],
        tools=[],
        model="claude-sonnet-4-6",
    )
    assert result.cached_input_write_5m_tokens == 0
    assert result.cached_input_write_1h_tokens == 0
    assert result.cached_input_write_tokens == 500
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
uv run pytest tests/agents/test_anthropic_sdk_client.py::test_ttl_breakdown_flows_into_tooling_result tests/agents/test_anthropic_sdk_client.py::test_ttl_breakdown_defaults_zero_when_field_missing -v
```

Expected: FAIL — `cached_input_write_5m_tokens == 0` (the new fields exist but aren't yet populated from the response).

- [ ] **Step 3: Wire the breakdown read + ToolingResult population**

In `sidequest-server/sidequest/agents/anthropic_sdk_client.py`, modify `complete_with_tools`. First, near the existing per-iter usage extraction (around line 141-149), add the breakdown read. Replace:

```python
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
```

With:

```python
                usage = response.usage
                input_tokens = int(getattr(usage, "input_tokens", 0))
                output_tokens = int(getattr(usage, "output_tokens", 0))
                cache_read = int(getattr(usage, "cache_read_input_tokens", 0))
                cache_write = int(getattr(usage, "cache_creation_input_tokens", 0))
                # Per-TTL breakdown — exposed by anthropic-python>=0.51 via the
                # nested cache_creation object. Older SDKs return no nested
                # object; we keep aggregate-only behavior and report 0 for the
                # breakdown so the operator can see "SDK doesn't expose it"
                # rather than guessing.
                cache_creation = getattr(usage, "cache_creation", None)
                cache_write_5m = (
                    int(getattr(cache_creation, "ephemeral_5m_input_tokens", 0))
                    if cache_creation
                    else 0
                )
                cache_write_1h = (
                    int(getattr(cache_creation, "ephemeral_1h_input_tokens", 0))
                    if cache_creation
                    else 0
                )
                cumulative_in += input_tokens
                cumulative_out += output_tokens
                cumulative_cache_read += cache_read
                cumulative_cache_write += cache_write
                cumulative_cache_write_5m += cache_write_5m
                cumulative_cache_write_1h += cache_write_1h
                last_model = response.model
```

Then add the two new cumulative counters near the existing `cumulative_cache_write = 0` initialization (around line 117-119). Find:

```python
        cumulative_cache_read = 0
        cumulative_cache_write = 0
```

Add after them:

```python
        cumulative_cache_write_5m = 0
        cumulative_cache_write_1h = 0
```

Finally, find the `ToolingResult(` return at the end of `complete_with_tools` (around line 189-200) — there are TWO return paths in the tool loop. Update each to include the new fields. The `return ToolingResult(...)` block becomes:

```python
                return ToolingResult(
                    text=last_text,
                    stop_reason=response.stop_reason,
                    input_tokens=cumulative_in,
                    output_tokens=cumulative_out,
                    cached_input_read_tokens=cumulative_cache_read,
                    cached_input_write_tokens=cumulative_cache_write,
                    model=last_model,
                    tool_calls=all_tool_uses,
                    cumulative_cost_usd=cumulative_cost_usd,
                    cached_input_write_5m_tokens=cumulative_cache_write_5m,
                    cached_input_write_1h_tokens=cumulative_cache_write_1h,
                )
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
uv run pytest tests/agents/test_anthropic_sdk_client.py -v
```

Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py
git commit -m "feat(anthropic_sdk_client): plumb 5m/1h cache-write breakdown to ToolingResult"
```

---

### Task 4: Add 5m/1h columns to the per-iter `narrator.sdk.usage` log line

**Files:**
- Modify: `sidequest-server/sidequest/agents/anthropic_sdk_client.py:172-181` (log line)
- Test: `sidequest-server/tests/agents/test_anthropic_sdk_client.py` (add new test below)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/agents/test_anthropic_sdk_client.py`:

```python
async def test_per_iter_log_line_includes_ttl_breakdown(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """narrator.sdk.usage log line gains `5m=N 1h=N` columns so cache
    breakdown is visible in /tmp/sidequest-server.log without a WS tap."""
    import logging

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sdk_response = _SdkResponse(
        content=[_SdkContentTextBlock(type="text", text="ok")],
        stop_reason="end_turn",
        usage=_Usage(
            input_tokens=10,
            output_tokens=2,
            cache_creation_input_tokens=300,
            cache_creation=_CacheCreation(
                ephemeral_5m_input_tokens=100,
                ephemeral_1h_input_tokens=200,
            ),
        ),
        model="claude-sonnet-4-6",
    )
    fake = _FakeAsyncSdk(responses=[sdk_response])
    client = AnthropicSdkClient(sdk=fake)
    with caplog.at_level(logging.INFO, logger="sidequest.agents.anthropic_sdk_client"):
        await client.complete_with_tools(
            system_blocks=[CacheableBlock(text="x", cache=True)],
            messages=[Message(role="user", content="hi")],
            tools=[],
            model="claude-sonnet-4-6",
        )
    usage_records = [r for r in caplog.records if "narrator.sdk.usage" in r.getMessage()]
    assert usage_records, "expected at least one narrator.sdk.usage log line"
    msg = usage_records[0].getMessage()
    assert "5m=100" in msg, f"expected '5m=100' in log line; got: {msg}"
    assert "1h=200" in msg, f"expected '1h=200' in log line; got: {msg}"
```

- [ ] **Step 2: Run test, verify fail**

```bash
uv run pytest tests/agents/test_anthropic_sdk_client.py::test_per_iter_log_line_includes_ttl_breakdown -v
```

Expected: FAIL — `5m=100 not in msg`.

- [ ] **Step 3: Extend the log line**

In `sidequest-server/sidequest/agents/anthropic_sdk_client.py`, find the `logger.info("narrator.sdk.usage ...")` call (around line 172-181) and replace with:

```python
                logger.info(
                    "narrator.sdk.usage iter=%d input=%d output=%d "
                    "cache_read=%d cache_write=%d 5m=%d 1h=%d cost_usd=%.6f",
                    iteration,
                    input_tokens,
                    output_tokens,
                    cache_read,
                    cache_write,
                    cache_write_5m,
                    cache_write_1h,
                    cost,
                )
```

- [ ] **Step 4: Run test, verify pass**

```bash
uv run pytest tests/agents/test_anthropic_sdk_client.py::test_per_iter_log_line_includes_ttl_breakdown -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py
git commit -m "feat(anthropic_sdk_client): emit 5m/1h breakdown in narrator.sdk.usage log line"
```

---

### Task 5: Add `cache_control` to the last entry of `_build_tools_array`

**Files:**
- Modify: `sidequest-server/sidequest/agents/anthropic_sdk_client.py:258-266`
- Test: `sidequest-server/tests/agents/test_anthropic_sdk_client.py` (add new tests below)

- [ ] **Step 1: Write the failing tests**

Append to `sidequest-server/tests/agents/test_anthropic_sdk_client.py`:

```python
async def test_last_tool_gets_cache_control_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The last tool definition carries a cache_control marker with the
    client's configured TTL. Earlier tools do not. This converts the
    tools array (byte-stable across every turn) into an explicit 1h
    cache prefix instead of relying on Anthropic's default 5m auto-cache."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake = _FakeAsyncSdk(
        responses=[
            _SdkResponse(
                content=[_SdkContentTextBlock(type="text", text="ok")],
                stop_reason="end_turn",
                usage=_Usage(input_tokens=10, output_tokens=2),
                model="claude-sonnet-4-6",
            )
        ]
    )
    client = AnthropicSdkClient(sdk=fake, cache_ttl="1h")
    tools = [
        ToolDefinition(name="alpha", description="a", input_schema={"type": "object"}),
        ToolDefinition(name="beta", description="b", input_schema={"type": "object"}),
        ToolDefinition(name="gamma", description="c", input_schema={"type": "object"}),
    ]
    await client.complete_with_tools(
        system_blocks=[CacheableBlock(text="x", cache=True)],
        messages=[Message(role="user", content="hi")],
        tools=tools,
        model="claude-sonnet-4-6",
    )
    sent_tools = fake.messages.calls[0]["tools"]
    assert len(sent_tools) == 3
    assert "cache_control" not in sent_tools[0]
    assert "cache_control" not in sent_tools[1]
    assert sent_tools[2]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


async def test_last_tool_marker_inherits_5m_ttl_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No parallel TTL config — the tools marker echoes the same
    self.cache_ttl as the system-block marker."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake = _FakeAsyncSdk(
        responses=[
            _SdkResponse(
                content=[_SdkContentTextBlock(type="text", text="ok")],
                stop_reason="end_turn",
                usage=_Usage(input_tokens=10, output_tokens=2),
                model="claude-sonnet-4-6",
            )
        ]
    )
    client = AnthropicSdkClient(sdk=fake, cache_ttl="5m")
    tools = [
        ToolDefinition(name="alpha", description="a", input_schema={"type": "object"}),
    ]
    await client.complete_with_tools(
        system_blocks=[CacheableBlock(text="x", cache=True)],
        messages=[Message(role="user", content="hi")],
        tools=tools,
        model="claude-sonnet-4-6",
    )
    sent_tools = fake.messages.calls[0]["tools"]
    assert sent_tools[0]["cache_control"] == {"type": "ephemeral", "ttl": "5m"}
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
uv run pytest tests/agents/test_anthropic_sdk_client.py::test_last_tool_gets_cache_control_marker tests/agents/test_anthropic_sdk_client.py::test_last_tool_marker_inherits_5m_ttl_when_configured -v
```

Expected: FAIL — `KeyError: 'cache_control'` on `sent_tools[2]`.

- [ ] **Step 3: Implement the marker**

In `sidequest-server/sidequest/agents/anthropic_sdk_client.py`, replace `_build_tools_array` (lines 258-266) with:

```python
    def _build_tools_array(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]
        # The tools array is byte-stable across every turn — 27 definitions,
        # ~7.6K tokens, no per-turn drift. Without an explicit cache_control
        # marker, Anthropic auto-caches it at default 5m TTL and re-writes
        # the whole block every time the 5m timer expires (which the
        # submit-and-wait MP cadence routinely outlives). A marker on the
        # last entry caches the whole tools array at the configured TTL
        # (1h by default). See ADR-101 four-region cache layout amendment.
        if out:
            out[-1]["cache_control"] = {"type": "ephemeral", "ttl": self.cache_ttl}
        return out
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
uv run pytest tests/agents/test_anthropic_sdk_client.py -v
```

Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/anthropic_sdk_client.py tests/agents/test_anthropic_sdk_client.py
git commit -m "feat(anthropic_sdk_client): cache tools array at 1h (last-entry cache_control marker)"
```

---

### Task 6: Empty tools array — skip marker without raising

**Files:**
- Test: `sidequest-server/tests/agents/test_anthropic_sdk_client.py` (add new test below)
- No production code change — Task 5's `if out:` guard already handles it.

This task verifies the guard works. Pure regression coverage.

- [ ] **Step 1: Write the test**

Append to `sidequest-server/tests/agents/test_anthropic_sdk_client.py`:

```python
async def test_empty_tools_array_skips_marker_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test fixtures sometimes pass tools=[]. The marker is best-effort
    opt-in; an empty array must not raise. Production has 27 tools."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake = _FakeAsyncSdk(
        responses=[
            _SdkResponse(
                content=[_SdkContentTextBlock(type="text", text="ok")],
                stop_reason="end_turn",
                usage=_Usage(input_tokens=10, output_tokens=2),
                model="claude-sonnet-4-6",
            )
        ]
    )
    client = AnthropicSdkClient(sdk=fake, cache_ttl="1h")
    # Must not raise.
    await client.complete_with_tools(
        system_blocks=[CacheableBlock(text="x", cache=True)],
        messages=[Message(role="user", content="hi")],
        tools=[],
        model="claude-sonnet-4-6",
    )
    sent_tools = fake.messages.calls[0]["tools"]
    assert sent_tools == []
```

- [ ] **Step 2: Run test, verify pass (no impl change needed)**

```bash
uv run pytest tests/agents/test_anthropic_sdk_client.py::test_empty_tools_array_skips_marker_without_raising -v
```

Expected: PASS — Task 5's `if out:` guard already protects this case. If it fails, Task 5's implementation is wrong; go back and fix.

- [ ] **Step 3: Commit**

```bash
git add tests/agents/test_anthropic_sdk_client.py
git commit -m "test(anthropic_sdk_client): empty tools array skips cache_control marker"
```

---

### Task 7: Orchestrator emits `narration.turn.cache_write_5m_tokens` and `cache_write_1h_tokens` span attributes

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py:3218-3236` (narration.turn span attribute block)
- Test: `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py` (add new test below)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py`:

```python
@pytest.mark.asyncio
async def test_narration_turn_span_carries_ttl_breakdown(
    simple_turn_context,
    otel_capture: InMemorySpanExporter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """narration.turn span exposes 5m vs 1h write breakdown so the GM
    panel can verify the tools-cache fix engaged."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sdk = _Sdk(
        responses=[
            _Resp(
                content=[_TextBlock(type="text", text="The torch sputters.")],
                stop_reason="end_turn",
                usage=_Usage(
                    input_tokens=300,
                    output_tokens=40,
                    cache_read_input_tokens=10000,
                    cache_creation_input_tokens=15000,
                    cache_creation=_CacheCreation(
                        ephemeral_5m_input_tokens=0,
                        ephemeral_1h_input_tokens=15000,
                    ),
                ),
                model="claude-sonnet-4-6",
            )
        ]
    )
    client = AnthropicSdkClient(sdk=sdk, cache_ttl="1h")
    orch = Orchestrator(client=client)

    await orch.run_narration_turn("look around", simple_turn_context)

    turn_spans = [s for s in otel_capture.get_finished_spans() if s.name == "narration.turn"]
    assert turn_spans, "expected a narration.turn span"
    attrs = dict(turn_spans[0].attributes or {})
    assert attrs.get("narration.turn.cache_write_5m_tokens") == 0, (
        f"expected 0; got {attrs.get('narration.turn.cache_write_5m_tokens')!r}"
    )
    assert attrs.get("narration.turn.cache_write_1h_tokens") == 15000, (
        f"expected 15000; got {attrs.get('narration.turn.cache_write_1h_tokens')!r}"
    )
```

- [ ] **Step 2: Run test, verify fail**

```bash
uv run pytest tests/agents/test_cache_ttl_prefix_and_otel.py::test_narration_turn_span_carries_ttl_breakdown -v
```

Expected: FAIL — `attrs.get('narration.turn.cache_write_5m_tokens')` is `None`.

- [ ] **Step 3: Emit the span attributes**

In `sidequest-server/sidequest/agents/orchestrator.py`, find the existing block (around lines 3218-3223) that sets `narration.turn.cache_read_tokens` and `narration.turn.cache_write_tokens`. Immediately after those two `span.set_attribute(...)` calls, add:

```python
                span.set_attribute(
                    "narration.turn.cache_write_5m_tokens",
                    result.cached_input_write_5m_tokens,
                )
                span.set_attribute(
                    "narration.turn.cache_write_1h_tokens",
                    result.cached_input_write_1h_tokens,
                )
```

(Insert directly after the `cache_write_tokens` setter; before the existing `cache_ttl` setter.)

- [ ] **Step 4: Run test, verify pass**

```bash
uv run pytest tests/agents/test_cache_ttl_prefix_and_otel.py -v
```

Expected: PASS (full file — verifies prior tests still pass too).

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_cache_ttl_prefix_and_otel.py
git commit -m "feat(orchestrator): emit cache_write_5m/1h_tokens on narration.turn span"
```

---

### Task 8: Orchestrator emits `narration.turn.system_block_sizes_json` diagnostic

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py:3114-3135` (block composition + new attribute)
- Test: `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py` (add new test below)

This is the **stability audit** diagnostic — surfaces drift in the supposedly-stable Primacy+Early zone.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py`:

```python
@pytest.mark.asyncio
async def test_narration_turn_span_carries_system_block_sizes_json(
    simple_turn_context,
    otel_capture: InMemorySpanExporter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stability-audit diagnostic — span carries per-block token sizes
    so drift in 'stable' zones surfaces in the GM panel."""
    import json as _json

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sdk = _Sdk(
        responses=[
            _Resp(
                content=[_TextBlock(type="text", text="ok")],
                stop_reason="end_turn",
                usage=_Usage(input_tokens=10, output_tokens=2),
                model="claude-sonnet-4-6",
            )
        ]
    )
    client = AnthropicSdkClient(sdk=sdk, cache_ttl="1h")
    orch = Orchestrator(client=client)

    await orch.run_narration_turn("look around", simple_turn_context)

    turn_spans = [s for s in otel_capture.get_finished_spans() if s.name == "narration.turn"]
    assert turn_spans, "expected a narration.turn span"
    attrs = dict(turn_spans[0].attributes or {})
    raw = attrs.get("narration.turn.system_block_sizes_json")
    assert isinstance(raw, str), f"expected JSON string; got {type(raw).__name__}"
    sizes = _json.loads(raw)
    # Required keys — all four regions must report a size even if zero.
    assert set(sizes.keys()) == {"stable", "valley", "recency", "tools"}, (
        f"unexpected key set: {sorted(sizes.keys())}"
    )
    # Each size is a non-negative int (token estimate via char-count / 4).
    for name, value in sizes.items():
        assert isinstance(value, int) and value >= 0, (
            f"{name}={value!r} must be a non-negative int"
        )
    # Stable region must be non-empty on a real narration turn.
    assert sizes["stable"] > 0, "stable region must carry content"
```

- [ ] **Step 2: Run test, verify fail**

```bash
uv run pytest tests/agents/test_cache_ttl_prefix_and_otel.py::test_narration_turn_span_carries_system_block_sizes_json -v
```

Expected: FAIL — `attrs.get('narration.turn.system_block_sizes_json')` is `None`.

- [ ] **Step 3: Emit the diagnostic**

In `sidequest-server/sidequest/agents/orchestrator.py`, find the block composition (around lines 3114-3135) where `stable_text`, `valley_text`, `recency_text`, and `system_blocks` are constructed. Just after that block, *before* the `messages = [Message(...)]` line, add the per-block size computation. Then in the span-attribute block (where Task 7's attributes were added), include the new attribute.

Specifically, after the line:

```python
            system_blocks: list[CacheableBlock] = [CacheableBlock(text=stable_text, cache=True)]
            if valley_text:
                system_blocks.append(CacheableBlock(text=valley_text, cache=False))
            if recency_text:
                system_blocks.append(CacheableBlock(text=recency_text, cache=False))
```

Add:

```python
            # Stability-audit diagnostic — per-block token estimate using the
            # project's standard char/4 approximation (see orchestrator.py
            # token-estimate pattern). Tools size is computed from the
            # registry's serialized JSON. Drift in the 'stable' region
            # surfaces as a growing value across turns of one session.
            tools_payload = json.dumps(
                [
                    {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                    for t in default_registry.tool_definitions()
                ]
            )
            system_block_sizes = {
                "stable": len(stable_text) // 4,
                "valley": len(valley_text) // 4,
                "recency": len(recency_text) // 4,
                "tools": len(tools_payload) // 4,
            }
```

(`json` and `default_registry` are already imported in `orchestrator.py`; if a flake check complains otherwise, add them — `default_registry` comes from `from sidequest.agents.tool_registry import ToolContext, default_registry` which is already in the function-local imports at the top of `_run_narration_turn_sdk`.)

Then in the span-attribute block (right after Task 7's new attributes), add:

```python
                span.set_attribute(
                    "narration.turn.system_block_sizes_json",
                    json.dumps(system_block_sizes),
                )
```

- [ ] **Step 4: Run test, verify pass**

```bash
uv run pytest tests/agents/test_cache_ttl_prefix_and_otel.py -v
```

Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_cache_ttl_prefix_and_otel.py
git commit -m "feat(orchestrator): emit system_block_sizes_json on narration.turn span"
```

---

### Task 9: ADR-101 inline amendment — four-region cache layout

**Files:**
- Modify: `docs/adr/101-anthropic-sdk-as-narrator-backend.md` (append amendment section)

This commit lives in the **orchestrator repo**, not the server repo. The orchestrator branch `feat/spec-narrator-cache-cost-reduction` is already checked out from the spec authoring.

- [ ] **Step 1: Open the ADR and append an amendment section**

In `docs/adr/101-anthropic-sdk-as-narrator-backend.md`, append a new section at the end of the document:

```markdown
## Amendment — 2026-05-20: Four-Region Cache Layout

The cacheable surface of the narrator request is documented as four
regions, in cache-prefix order:

| Region | Source | Cache | TTL | Notes |
|--------|--------|-------|-----|-------|
| **Tools** | `_build_tools_array` (last entry marked) | yes | 1h | 27 stable definitions, ~7,681 tokens. Marker added 2026-05-20 because Anthropic's default auto-cache on tools was landing in 5m and re-writing every turn the 5m TTL expired. |
| **Stable** (Primacy + Early) | `system_blocks[0]` | yes | 1h | SOUL, identity, guardrails, ~10,639 tokens. Byte-stability is gated by `tests/agents/test_cache_ttl_prefix_and_otel.py::test_compose_split_system_prefix_byte_identical_across_3_turns`. |
| **Valley** | `system_blocks[1]` | no | — | Per-turn drift (narrator vocabulary). Deliberately uncached per Phase D Task 6. |
| **Late + Recency** | `system_blocks[2]` | no | — | Per-turn drift (genre transition hints). Deliberately uncached per Phase D Task 6. |

The orchestrator emits a `narration.turn.system_block_sizes_json` OTEL
attribute carrying token-estimate sizes for all four regions on every
narration turn, so drift inside the "stable" region surfaces in the GM
panel rather than as a cache-write growth on the Anthropic console.

See [spec](../superpowers/specs/2026-05-20-narrator-cache-cost-reduction-design.md) and [plan](../superpowers/plans/2026-05-20-narrator-cache-cost-reduction.md) for the change set.
```

- [ ] **Step 2: Commit (orchestrator branch)**

```bash
# From /Users/slabgorb/Projects/oq-2 (orchestrator root)
git branch --show-current  # confirm: feat/spec-narrator-cache-cost-reduction
git add docs/adr/101-anthropic-sdk-as-narrator-backend.md
git commit -m "docs(adr-101): amendment — four-region cache layout (tools + stable + valley + recency)"
```

---

### Task 10: Full quality gate + smoke verify against a live narrator turn

**Files:** No code changes. Verification only.

- [ ] **Step 1: Run server quality gate**

```bash
# From /Users/slabgorb/Projects/oq-2 (orchestrator root)
just server-check
```

Expected: lint clean, all tests PASS.

- [ ] **Step 2: Start the server and confirm a real narration turn carries the new attributes**

```bash
# Terminal 1 — start the stack
just up
```

In a second terminal:

```bash
# Tail the server log for the new 5m=N 1h=N columns
tail -f /tmp/sidequest-server.log | grep "narrator.sdk.usage"
```

Open the UI at `http://localhost:5173`, load any existing save or start a fresh session, and submit one player action.

Expected log line shape (one per iter):

```
narrator.sdk.usage iter=1 input=N output=N cache_read=N cache_write=N 5m=N 1h=N cost_usd=N.NN
```

- [ ] **Step 3: Confirm the success criteria predictions hold**

On the second turn of the session, the log line should show:

- `cache_read` ≈ 18,000+ (was ~10,639 — now includes both stable system block and tools)
- `1h` value populated; on a warm turn, may be ~0 (everything already cached) or include block 0 cache write
- `5m` value should be ≈ 0 on warm turns (down from the prior ~15,000 default-5m writes)

Compare against the pre-fix dashboard baseline screenshot (taken 2026-05-20 4AM, captured in the spec problem statement).

- [ ] **Step 4: Shut down cleanly**

```bash
just down
```

- [ ] **Step 5: Push both branches**

```bash
# Server branch
git -C sidequest-server push -u origin feat/narrator-cache-cost-reduction

# Orchestrator branch (already pushed if spec PR was created; otherwise:)
git push -u origin feat/spec-narrator-cache-cost-reduction
```

- [ ] **Step 6: Open PRs**

```bash
# Server PR — base is develop (gitflow per repos.yaml)
gh -C sidequest-server pr create --base develop \
  --title "feat: narrator cache cost reduction (tools cache + 5m/1h telemetry)" \
  --body "Implements spec docs/superpowers/specs/2026-05-20-narrator-cache-cost-reduction-design.md per plan docs/superpowers/plans/2026-05-20-narrator-cache-cost-reduction.md"

# Orchestrator PR — base is main
env -u GITHUB_TOKEN gh pr create --base main \
  --title "docs: narrator cache cost reduction (spec + plan + ADR-101 amendment)" \
  --body "Spec, plan, and ADR-101 inline amendment for the narrator cache fix in sidequest-server."
```

---

## Self-Review

**Spec coverage check (against the design doc sections):**

| Spec section | Task(s) |
|--------------|---------|
| Problem / baseline | Spec only — referenced in Task 10 verification |
| Architecture: four-region layout table | Task 9 (ADR amendment), Task 5 (impl) |
| Component 1: tools cache_control | Task 5 |
| Component 2: usage extraction (5m/1h) | Tasks 1, 2, 3 |
| Component 3: span attribution (5m/1h) | Task 7 |
| Component 3: span attribution (system_block_sizes_json) | Task 8 |
| Data flow diagram | Tasks 3-8 cover every arrow |
| Success criteria (observable predictions) | Task 10 |
| Error handling: SDK version drift (no cache_creation) | Task 3 (test 2) |
| Error handling: empty tools array | Task 6 |
| Error handling: beta header rejected | unchanged behavior — no task needed |
| Testing: four unit tests | Tasks 1, 3, 4, 5 (multiple per task) |
| Testing: extend wiring test | Tasks 7, 8 |

All spec sections have at least one implementing task. No gaps.

**Placeholder scan:** None — every code block is complete. Every command has expected output. Every test has assertions.

**Type consistency:** `cached_input_write_5m_tokens` and `cached_input_write_1h_tokens` used consistently across all tasks (dataclass field, fake, SDK client, span attr name). `narration.turn.cache_write_5m_tokens` / `narration.turn.cache_write_1h_tokens` used consistently as span attribute names. `narration.turn.system_block_sizes_json` used consistently for the diagnostic. JSON keys `stable`/`valley`/`recency`/`tools` are stable across Task 8 impl and Task 9 ADR text.

**Scope:** Single subsystem (narrator cache), 10 tasks, ~3-4 hours of focused work. Single implementation plan is right-sized.
