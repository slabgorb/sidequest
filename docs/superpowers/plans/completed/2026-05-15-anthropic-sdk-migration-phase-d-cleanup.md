# Anthropic SDK Migration — Phase D: Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flip the narrator path to the SDK on the feature branch, then delete the structures the SDK makes redundant: ADR-039 sidecar parser, ADR-028 perception rewriter, ADR-058 subprocess OTEL scraping (narrator path), the now-dead prompt-build helpers. Write the four successor ADRs.

**Architecture:** Phase D is mostly deletion plus one re-wire (narrator orchestrator → SDK client + Registry). Each deletion is preceded by a wiring-test confirmation that nothing on the new path depends on the to-be-deleted module. The four successor ADRs are written from the spec; no design decisions deferred.

**Tech Stack:** Same as Phases A-C.

**Scope:** Phase D only — 5 stories (D1-D5, 16 pts). Phase C must be fully landed (all 26 tools registered, sidecar coverage map green) before this plan starts.

**Branch:** `feat/anthropic-sdk-migration` (same branch as Phases A-C) in `sidequest-server/` and `orc-quest/` for the ADR commits.

---

## File Structure

**Created (orchestrator repo):**
- `docs/adr/102-tool-use-protocol-for-structured-output.md` — successor to ADR-039
- `docs/adr/103-native-otel-via-tool-registry.md` — successor to ADR-058
- `docs/adr/104-perception-filtering-at-the-tool-layer.md` — successor to ADR-028

Status: all three start as `proposed`. Promote to `accepted` only on Phase E merge.

(NOTE: this plan was drafted assuming the parent migration ADR would land
as ADR-099, but it actually merged as ADR-101 — see
`docs/adr/101-anthropic-sdk-as-narrator-backend.md`. Successor numbers
have been bumped from 100/101/102 to 102/103/104 to avoid collision with
the merged ADRs 099 (coyote-object-salvage-hooks) and 100
(journal-pipeline-coherence). Every reference to "ADR-099" in this plan
body means **ADR-101**.)

**Modified (orchestrator repo):**
- `docs/adr/039-narrator-structured-output.md` — frontmatter `superseded_by: 102`
- `docs/adr/058-claude-subprocess-otel-passthrough.md` — frontmatter `superseded_by: 103`
- `docs/adr/028-perception-rewriter.md` — frontmatter `superseded_by: 104`
- `docs/adr/073-local-fine-tuned-model-architecture.md` — frontmatter `amended_by: 101` (header amendment only; body left alone)
- `docs/adr/013-lazy-json-extraction.md` — frontmatter `status: drift` and a one-line note pointing at the sidecar retirement (per spec §ADR consequences)
- `docs/adr/README.md` — regenerated index
- `CLAUDE.md` — ADR index block regenerated

**Modified (server repo):**
- `sidequest/agents/orchestrator.py` — narrator path now uses `AnthropicSdkClient` + `default_registry` + `NarratorPerceptionFilter`; remove all references to `claude_stream_parser` sidecar parsing for the narrator path
- `sidequest/agents/narrator.py` — same; trim any sidecar-parsing helpers
- `sidequest/agents/llm_factory.py` — default backend flips from `claude` to `anthropic_sdk`

**Deleted (server repo):**
- `sidequest/agents/claude_stream_parser.py` — sidecar parser (ADR-039)
- `sidequest/agents/perception_rewriter.py` — post-pass rewriter (ADR-028)
- The ADR-058 subprocess JSON scraping code path inside `sidequest/agents/claude_client.py` — only the *narrator stderr scraping*; `ClaudeClient` itself stays for non-narrator paths
- Any narrator-prompt helpers that built the now-deleted pre-injected content blocks (Phase C left some that became unreachable; this phase audits and removes them)
- `tests/agents/test_claude_stream_parser.py`
- `tests/agents/test_perception_rewriter.py` (and equivalent)

---

## Self-Review (pre-execution)

Spec coverage:
- D1 (sidecar parser deletion) → Task 4
- D2 (ADR-028 rewriter deletion) → Task 3
- D3 (ADR-058 scraping deletion) → Task 5
- D4 (final prompt slim) → Task 6
- D5 (successor ADRs) → Task 7

Ordering is important: flip the narrator backend FIRST (Task 1-2), then delete (3-5). Deleting before flipping leaves the live narrator broken on develop-equivalent paths (the playgroup doesn't see it, but CI does).

Placeholder scan: every step lists the specific file paths and the specific code to delete or change.

---

## Task 1 — Flip the narrator orchestrator to SDK + Registry

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py`
- Modify: `sidequest-server/sidequest/agents/narrator.py`
- Test: `sidequest-server/tests/agents/test_narrator_uses_sdk_client.py` (new)

The narrator's `run_turn` (or equivalent — find the entry) currently constructs the prompt then calls `LlmClient.send_with_session` or similar. Phase D rewires it to:
1. Build the slim prompt (Phase C already changed `build_narrator_prompt`'s output shape)
2. Map the prompt into `system_blocks` (cacheable) + `messages` (rolling)
3. Acquire a `ToolingLlmClient` from the factory (Phase A wired `anthropic_sdk` as a backend key)
4. Call `complete_with_tools` with `default_registry.tool_definitions()` + an async `tool_dispatch` that calls `default_registry.dispatch(block, ctx)`
5. Open a `narration_turn_cost_span` (Phase A) and roll up the resulting `ToolingResult` into its attrs

- [ ] **Step 1.1: Inspect the current orchestrator entry**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -n "def run_turn\|def narrate\|build_narrator_prompt\|send_with_session" sidequest/agents/orchestrator.py sidequest/agents/narrator.py | head -30
```

Identify the single entry point that produces narration for one turn. Note its parameters (likely `world_state`, `session_id`, `acting_pc`, `player_action`).

- [ ] **Step 1.2: Write a wiring test for the new entry**

Create `sidequest-server/tests/agents/test_narrator_uses_sdk_client.py`:
```python
"""Phase D wiring — narrator orchestrator calls AnthropicSdkClient via Registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from sidequest.agents.narrator import run_narration_turn  # adjust name once located
from sidequest.agents.tool_registry import default_registry


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


async def test_narrator_uses_anthropic_sdk_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """One quiet-travel turn: no tool calls, just text out."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    from sidequest.agents.anthropic_sdk_client import AnthropicSdkClient

    sdk = _Sdk(
        responses=[
            _Resp(
                content=[_Text(type="text", text="You arrive in Montmartre. Rain.")],
                stop_reason="end_turn",
                usage=_Usage(input_tokens=300, output_tokens=10),
                model="claude-sonnet-4-6",
            )
        ]
    )
    client = AnthropicSdkClient(sdk=sdk)

    # Patch the factory so run_narration_turn picks up the injected client.
    from sidequest.agents import llm_factory

    monkeypatch.setattr(llm_factory, "build_llm_client", lambda: client)

    # Construct a minimal world-state stub appropriate for the run_narration_turn
    # signature. (Actual fixture wiring: locate the cheapest test-friendly stub
    # used elsewhere in tests/agents/ — likely tests/agents/conftest.py exposes
    # one.)
    state = MagicMock()
    state.world_id = "test_world"
    state.session_id = "sess"
    state.current_pc = "alex"

    result = await run_narration_turn(
        state=state,
        player_action="I look at the rain.",
    )

    assert "Montmartre" in result.narration
    assert len(sdk.messages.calls) == 1
    # Tools array passed down should be the 26 registered tools.
    assert len(sdk.messages.calls[0]["tools"]) == len(default_registry.list_names())
```

(Adjust the `run_narration_turn` import + signature to match what you find in Step 1.1.)

- [ ] **Step 1.3: Run the test (should fail)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_narrator_uses_sdk_client.py -v
```

Expected: AttributeError (narrator hasn't been switched) or AssertionError (tools array empty).

- [ ] **Step 1.4: Rewire the narrator entry**

In whichever module owns the narrator turn (per Step 1.1), replace the existing call site. The new shape:

```python
from sidequest.agents.anthropic_sdk_client import AnthropicSdkClient
from sidequest.agents.llm_factory import build_llm_client
from sidequest.agents.model_routing import CallType, resolve_model
from sidequest.agents.narrator_perception_filter import NarratorPerceptionFilter
from sidequest.agents.tool_registry import (
    ToolContext,
    default_registry,
)
from sidequest.agents.tooling_protocol import (
    CacheableBlock,
    Message,
    ToolResultBlock,
    ToolUseBlock,
    ToolingLlmClient,
)
from sidequest.telemetry.spans.cost import narration_turn_cost_span
# Import every tool module so they register at first call:
import sidequest.agents.tools  # noqa: F401


async def run_narration_turn(state, player_action: str):
    client = build_llm_client()
    if not isinstance(client, ToolingLlmClient):
        raise RuntimeError(
            "Narrator requires a ToolingLlmClient. Set SIDEQUEST_LLM_BACKEND=anthropic_sdk."
        )
    system_blocks, messages = _build_prompt(state, player_action)
    perception_filter = NarratorPerceptionFilter()
    model = resolve_model(CallType.NARRATION)
    ctx = ToolContext(
        world_id=state.world_id,
        session_id=state.session_id,
        perspective_pc=state.current_pc,
        turn_number=state.turn_number,
        store=state.store,
        otel_span=None,  # filled in by span context manager below
        perception_filter=perception_filter,
    )

    async def dispatch(block: ToolUseBlock) -> ToolResultBlock:
        return await default_registry.dispatch(block, ctx)

    with narration_turn_cost_span(
        world_id=state.world_id,
        session_id=state.session_id,
        turn_number=state.turn_number,
        acting_pc=state.current_pc,
    ) as turn_span:
        result = await client.complete_with_tools(
            system_blocks=system_blocks,
            messages=messages,
            tools=default_registry.tool_definitions(),
            tool_dispatch=dispatch,
            model=model,
        )
        # Rollup attrs
        turn_span.set_attribute("narration.turn.model_chosen", result.model)
        turn_span.set_attribute("narration.turn.total_input_tokens", result.input_tokens)
        turn_span.set_attribute("narration.turn.total_output_tokens", result.output_tokens)
        turn_span.set_attribute("narration.turn.cache_read_tokens", result.cached_input_read_tokens)
        turn_span.set_attribute("narration.turn.cache_write_tokens", result.cached_input_write_tokens)
        turn_span.set_attribute("narration.turn.tool_call_count", len(result.tool_calls))
    return _NarrationResult(narration=result.text, tool_calls=result.tool_calls)
```

`_build_prompt` builds the three cacheable zones + the rolling messages — this helper replaces the old fat-prompt builder. The Phase C slim work produced the inputs; this helper assembles them into `CacheableBlock`/`Message` shapes.

- [ ] **Step 1.5: Run the wiring test (should pass)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_narrator_uses_sdk_client.py -v
```

- [ ] **Step 1.6: Run all narrator-adjacent tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/ tests/handlers/ -v
```

Expected: any test that still imports the old narrator sidecar path fails — track failures, route fixes through the per-test repair below, do NOT skip.

- [ ] **Step 1.7: Repair affected tests**

For each failing test, decide: (a) does it test removed functionality (sidecar parsing, perception rewriter)? → mark for deletion in Task 3-4; (b) does it test the new functionality at the wrong layer? → port to the new shape.

- [ ] **Step 1.8: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/agents/orchestrator.py sidequest/agents/narrator.py tests/agents/test_narrator_uses_sdk_client.py tests/agents/...  # any repaired tests
git commit -m "feat(narrator): rewire to AnthropicSdkClient + Registry + NarratorPerceptionFilter

Phase D step 1 of 5. Narrator orchestrator now calls
ToolingLlmClient.complete_with_tools with all 26 registered tools and
the slim-zone system prompt. The narration.turn span carries cost/token
rollups. ADR-039 sidecar parsing is no longer invoked on the narrator
path — its files are deleted in a follow-up task."
```

---

## Task 2 — Flip factory default to `anthropic_sdk`

**Files:**
- Modify: `sidequest-server/sidequest/agents/llm_factory.py`
- Modify: `sidequest-server/tests/agents/test_llm_factory.py`

- [ ] **Step 2.1: Update the test**

In `tests/agents/test_llm_factory.py`, the `test_default_is_still_claude` test (Phase A) needs to flip:

```python
def test_default_is_anthropic_sdk_after_phase_d(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sidequest.agents.anthropic_sdk_client import AnthropicSdkClient
    from sidequest.agents.llm_factory import build_llm_client

    monkeypatch.delenv("SIDEQUEST_LLM_BACKEND", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    client = build_llm_client()
    assert isinstance(client, AnthropicSdkClient)


def test_explicit_claude_backend_still_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-narrator paths can still opt into ClaudeClient explicitly."""
    from sidequest.agents.claude_client import ClaudeClient
    from sidequest.agents.llm_factory import build_llm_client

    monkeypatch.setenv("SIDEQUEST_LLM_BACKEND", "claude")
    client = build_llm_client()
    assert isinstance(client, ClaudeClient)
```

Delete the old `test_default_is_still_claude` test.

- [ ] **Step 2.2: Update the factory**

In `sidequest/agents/llm_factory.py`, change:
```python
    raw = os.environ.get(ENV_BACKEND, "claude")
```
to:
```python
    raw = os.environ.get(ENV_BACKEND, "anthropic_sdk")
```

- [ ] **Step 2.3: Run + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_llm_factory.py -v
git add sidequest/agents/llm_factory.py tests/agents/test_llm_factory.py
git commit -m "feat(agents): flip llm_factory default to anthropic_sdk

Phase D step 2 of 5. Default backend is now anthropic_sdk. ClaudeClient
remains available via SIDEQUEST_LLM_BACKEND=claude for non-narrator
auxiliary paths (mood, name gen, scratch); narrator path requires a
ToolingLlmClient and will reject ClaudeClient at runtime (see Task 1)."
```

---

## Task 3 — Delete ADR-028 perception rewriter

**Files:**
- Delete: `sidequest-server/sidequest/agents/perception_rewriter.py`
- Delete: associated tests
- Modify: any caller imports

- [ ] **Step 3.1: Confirm zero non-test imports**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -rn "perception_rewriter\|PerceptionRewriter" --include='*.py' | grep -v '^tests/' | grep -v '^sidequest/agents/perception_rewriter.py:'
```

Expected: empty output. If any production caller still uses it, fix that caller (route through `NarratorPerceptionFilter`) before deleting.

- [ ] **Step 3.2: Delete the module + tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
rm sidequest/agents/perception_rewriter.py
rm tests/agents/test_perception_rewriter.py 2>/dev/null || true
# Search for other test files that reference the rewriter:
grep -rln "perception_rewriter\|PerceptionRewriter" tests/ | xargs -I{} echo "review: {}"
```

For each remaining test file: either delete (if it tested only the rewriter) or port to test `NarratorPerceptionFilter` instead.

- [ ] **Step 3.3: Run full suite**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v
```

Expected: no ImportError, no remaining references.

- [ ] **Step 3.4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add -u
git commit -m "feat(agents): delete ADR-028 post-pass perception rewriter

Phase D step 3 of 5. Perception filtering moved to the tool layer
(NarratorPerceptionFilter, Phase C Task 0). Multiplayer turns drop from
N+1 model calls to N. ADR-028 successor (ADR-102) drafted in Task 7."
```

---

## Task 4 — Delete ADR-039 sidecar parser

**Files:**
- Delete: `sidequest-server/sidequest/agents/claude_stream_parser.py`
- Modify: any caller imports

- [ ] **Step 4.1: Verify the coverage map is complete**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_sidecar_coverage_map.py -v
```

Expected: pass with no xfail. If any field is None, return to Phase C and convert the missing tool — do not proceed.

- [ ] **Step 4.2: Confirm zero non-test imports**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -rn "claude_stream_parser\|extract_sidecar\|SidecarJson" --include='*.py' | grep -v '^tests/' | grep -v '^sidequest/agents/claude_stream_parser.py:'
```

Expected: empty. Fix any remaining narrator path imports before proceeding.

- [ ] **Step 4.3: Delete**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
rm sidequest/agents/claude_stream_parser.py
rm tests/agents/test_claude_stream_parser.py
```

- [ ] **Step 4.4: Mark ADR-013 as drift**

(Spec §ADR consequences flags ADR-013 lazy JSON extraction as obsolete with sidecar retirement.)

Edit `orc-quest/docs/adr/013-lazy-json-extraction.md` frontmatter:
- Change `status` to `drift`
- Add `superseded_by: 102` (ADR-102, the sidecar successor, written in Task 7)

Do not edit the body.

Update `docs/adr/DRIFT.md` to list ADR-013 with a one-line note: "Lazy JSON extraction — sidecar retired in ADR-101 migration; mechanism replaced by SDK tool_use round-trips."

- [ ] **Step 4.5: Run full suite + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v
git add -u
git commit -m "feat(agents): delete ADR-039 sidecar parser

Phase D step 4 of 5. Every sidecar field migrated to a typed tool in
Phase C; the malformed-JSON-recovery parser (~200 LOC) is gone.
Structural lie detection now works: a narrator that claims a mechanical
effect without invoking the corresponding tool produces no
tool.write.* span — the GM panel can flag it."
```

In `orc-quest/`:

```bash
cd /Users/slabgorb/Projects/oq-1/
git add docs/adr/013-lazy-json-extraction.md docs/adr/DRIFT.md
git commit -m "docs(adr): mark ADR-013 as drift — sidecar retirement"
```

---

## Task 5 — Delete ADR-058 subprocess JSON scraping (narrator path)

**Files:**
- Modify: `sidequest-server/sidequest/agents/claude_client.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/agent.py` (or wherever subprocess scraping handlers live)

`ClaudeClient` remains for non-narrator paths. Only the *narrator-specific* subprocess JSON-stderr scraping is deleted. The general `agent_call_span` likely stays (auxiliary paths still emit it).

- [ ] **Step 5.1: Locate the scraping code**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -n "OTEL_TRACES\|otel_stderr\|stderr.*json\|scrape" sidequest/agents/claude_client.py sidequest/telemetry/ -r
```

Identify the specific function that parses Claude subprocess stderr for OTEL spans on narrator calls. Look for ADR-058's scraping handler.

- [ ] **Step 5.2: Delete the scraping path**

Remove the scraping function and any narrator-path code that activated it. Auxiliary paths (mood classifier, name gen, scratch) keep `agent_call_span` as-is — that's their telemetry surface.

- [ ] **Step 5.3: Run full suite**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v
```

- [ ] **Step 5.4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add -u
git commit -m "feat(telemetry): delete ADR-058 subprocess JSON scraping for narrator path

Phase D step 5a of 5. Narrator OTEL now flows via native llm.request and
tool.{cat}.{name} spans (Phases A-B). Auxiliary ClaudeClient paths keep
agent_call_span — they still use the subprocess. ADR-058 successor
(ADR-103) drafted in Task 7."
```

---

## Task 6 — Final prompt slim audit + cleanup

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py`, `sidequest/agents/narrator_prompts/*.py`
- Possibly delete: helpers that built the now-dead pre-injected blocks

- [ ] **Step 6.1: Measure current prompt size**

Add or use an existing instrumented harness. The simplest check is to dump one fixture's prompt and count tokens:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run python -m sidequest.cli.scene_harness scenarios/sidecar_parity/roll_dice_v1.yaml --dump-prompt /tmp/post-phase-c-prompt.json
wc -c /tmp/post-phase-c-prompt.json
```

(Token counting can use `anthropic.Anthropic().messages.count_tokens(...)` against the dumped payload.)

Target: median ~20k tokens across the parity fixtures (spec §Slim prompt target).

- [ ] **Step 6.2: Identify residual fat**

Common residual offenders:
- Helpers that built the old pre-injected blocks may still run for non-narrator paths but no longer be reachable — confirm via `grep -rn` and delete if unused
- The verbosity / tone / lethality blocks should stay; they're cache-zone 1
- The world snapshot block should be slim (name, region, calendar, flags, scenario pointer); if it's still pulling NPC details or scene state, those should now come through `query_npc` / `query_scene_state`

- [ ] **Step 6.3: Delete unreachable helpers**

For each helper identified as unreachable, delete it. Run the suite after each deletion to catch surprises.

- [ ] **Step 6.4: Verify the cache-zone shape**

The prompt produced by `_build_prompt` (from Task 1) must produce exactly three cacheable system blocks and one messages array. Add a structural test if one isn't already present:

```python
async def test_build_prompt_produces_three_cache_zones() -> None:
    state = ...  # standard fixture
    system_blocks, messages = _build_prompt(state, player_action="look around")
    assert len(system_blocks) == 3
    assert all(b.cache for b in system_blocks)
    assert len(messages) >= 1
```

- [ ] **Step 6.5: Run full suite + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v
uv run ruff check .
uv run pyright
git add -u
git commit -m "feat(narrator): final slim audit — three cache zones, ~20k median tokens

Phase D step 6 of 5. Delete unreachable prompt-build helpers, verify the
three-zone cacheable structure, lock in the spec's ~20k-token median
target via scenarios/sidecar_parity/* fixtures."
```

---

## Task 7 — Write the three successor ADRs

**Files (all in orc-quest):**
- Create: `docs/adr/102-tool-use-protocol-for-structured-output.md`
- Create: `docs/adr/103-native-otel-via-tool-registry.md`
- Create: `docs/adr/104-perception-filtering-at-the-tool-layer.md`
- Modify: `docs/adr/039-narrator-structured-output.md` (frontmatter)
- Modify: `docs/adr/058-claude-subprocess-otel-passthrough.md` (frontmatter)
- Modify: `docs/adr/028-perception-rewriter.md` (frontmatter)
- Modify: `docs/adr/073-local-fine-tuned-model-architecture.md` (frontmatter)
- Modify: `docs/adr/README.md` (regen)

- [ ] **Step 7.1: Draft ADR-102 (sidecar → tool-use successor)**

Create `orc-quest/docs/adr/102-tool-use-protocol-for-structured-output.md` with frontmatter:
```yaml
---
id: 102
title: Tool-Use Protocol for Structured Output
status: proposed
date: 2026-05-15
categories:
  - Agent System
  - Prompt Engineering
supersedes: [39]
depends_on: [101]
load_bearing: true
---
```

Body covers (one short section each):
- **Context** — ADR-039 used fenced-JSON sidecars parsed from narration text; fragile and forgeable (the narrator could write prose claiming a mechanical effect without the corresponding sidecar field).
- **Decision** — Structured output now uses Anthropic SDK tool_use round-trips with Pydantic-validated args; the registry dispatches each call through a typed adapter; the narrator cannot describe a mechanical effect without invoking the corresponding tool.
- **Consequences** — Sidecar parser deleted (~200 LOC); 26 tools cover every former sidecar field; OTEL spans replace post-hoc structured-output recovery; `apply_world_patch` provides an escape hatch for not-yet-typed mutations.
- **Reference** — design spec + Phase C plan.

- [ ] **Step 7.2: Draft ADR-103 (OTEL passthrough → native registry emission)**

Create `orc-quest/docs/adr/103-native-otel-via-tool-registry.md` with frontmatter:
```yaml
---
id: 103
title: Native OTEL via Tool Registry
status: proposed
date: 2026-05-15
categories:
  - Observability
  - Agent System
supersedes: [58]
depends_on: [101, 102]
load_bearing: true
---
```

Body:
- **Context** — ADR-058 scraped Claude CLI subprocess stderr for OTEL trace events; structurally forensic.
- **Decision** — Native OTEL emission via the tool registry: each tool call produces a `tool.{cat}.{name}` span; each model HTTP call produces an `llm.request` span; the turn produces a `narration.turn` rollup span. Three new structural lie-detection classes become possible (mechanical assertion without span, state described without query span, perception-filter violation against `perspective_pc`).
- **Consequences** — ADR-031's principle preserved, mechanism replaced. The GM panel becomes a *structural* lie detector. ADR-058 deleted from the narrator path; auxiliary `ClaudeClient` callers continue to use `agent_call_span`.
- **Reference** — design spec §OTEL / observability.

- [ ] **Step 7.3: Draft ADR-104 (post-pass rewriter → tool-layer filter)**

Create `orc-quest/docs/adr/104-perception-filtering-at-the-tool-layer.md` with frontmatter:
```yaml
---
id: 104
title: Perception Filtering at the Tool Layer
status: proposed
date: 2026-05-15
categories:
  - Multiplayer
  - Agent System
supersedes: [28]
depends_on: [101, 102]
load_bearing: false
---
```

Body:
- **Context** — ADR-028's post-pass rewriter generated omniscient narration, then ran a per-PC rewrite pass to redact (N+1 calls per multiplayer turn). Quality cost: model rewriting its own narration; cost: 2× the calls.
- **Decision** — Perception filtering moves to the tool layer. Each tool result is filtered by `NarratorPerceptionFilter` before being handed back to the model. The narrator generates from a perception-correct view directly; no redaction pass.
- **Consequences** — Multiplayer cost drops from N+1 to N. Quality improves because the narrator never sees content it would have had to redact. Sealed-visibility (PvP) becomes trivial to add. CLAUDE.md collaborative-visibility doctrine preserved unchanged (peer text remains visible during submit-and-wait per ADR-036 doctrine).
- **Reference** — design spec §Perception filtering at the tool layer.

- [ ] **Step 7.4: Update the frontmatter on the superseded ADRs**

In `orc-quest/docs/adr/039-narrator-structured-output.md`: add `superseded_by: 102`. Leave `status: accepted` (it flips to `superseded` on Phase E merge).

In `orc-quest/docs/adr/058-claude-subprocess-otel-passthrough.md`: add `superseded_by: 103`. Same status handling.

In `orc-quest/docs/adr/028-perception-rewriter.md`: add `superseded_by: 104`. Same status handling.

In `orc-quest/docs/adr/073-local-fine-tuned-model-architecture.md`: add `amended_by: 101`. (Header amendment only — body untouched.)

- [ ] **Step 7.5: Regenerate the ADR index**

```bash
cd /Users/slabgorb/Projects/oq-1/
python scripts/regenerate_adr_indexes.py
```

Verify: `docs/adr/README.md` and `CLAUDE.md` index block list ADRs 101, 102, 103, 104 as proposed.

- [ ] **Step 7.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/
git add docs/adr/102-tool-use-protocol-for-structured-output.md docs/adr/103-native-otel-via-tool-registry.md docs/adr/104-perception-filtering-at-the-tool-layer.md docs/adr/039-narrator-structured-output.md docs/adr/058-claude-subprocess-otel-passthrough.md docs/adr/028-perception-rewriter.md docs/adr/073-local-fine-tuned-model-architecture.md docs/adr/README.md CLAUDE.md
git commit -m "docs(adr): draft ADR-102/103/104 successors (proposed)

Successors to ADR-039 (sidecar), ADR-058 (OTEL passthrough), ADR-028
(perception rewriter). All proposed; promote to accepted alongside the
ADR-101 + 001-superseded flip on Phase E merge.

Refs spec: docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md"
```

---

## Task 8 — Phase D acceptance: full sweep + push

- [ ] **Step 8.1: Confirm sidecar parser file deleted**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
test ! -f sidequest/agents/claude_stream_parser.py && echo OK
```

- [ ] **Step 8.2: Confirm perception rewriter file deleted**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
test ! -f sidequest/agents/perception_rewriter.py && echo OK
```

- [ ] **Step 8.3: Full server suite**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v
```

- [ ] **Step 8.4: Lint / format / type**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

- [ ] **Step 8.5: Orchestrator gate**

```bash
cd /Users/slabgorb/Projects/oq-1/
just check-all
```

- [ ] **Step 8.6: Push both branches**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git push origin feat/anthropic-sdk-migration
cd /Users/slabgorb/Projects/oq-1/
git push origin feat/anthropic-sdk-migration
```

---

## Phase D completion check

- [ ] **Narrator default backend is `anthropic_sdk`.** Confirm:
  ```bash
  cd /Users/slabgorb/Projects/oq-1/sidequest-server
  unset SIDEQUEST_LLM_BACKEND
  ANTHROPIC_API_KEY=sk-test uv run python -c "from sidequest.agents.llm_factory import build_llm_client; print(type(build_llm_client()).__name__)"
  ```
  Expected: `AnthropicSdkClient`.
- [ ] **Sidecar parser deleted.** (Task 8.1)
- [ ] **Perception rewriter deleted.** (Task 8.2)
- [ ] **Three successor ADRs drafted as proposed.** ADR-102, ADR-103, ADR-104 all live in `docs/adr/` with `status: proposed`.
- [ ] **Slim prompt target met.** Median across parity fixtures ~20k tokens.
- [ ] **All tests green; no skips beyond pre-existing.**

---

## What's next

Phase E plan: `2026-05-15-anthropic-sdk-migration-phase-e-merge.md` — scenario replay, live playgroup session, squash-merge to `develop`, ADR status flips.
