# OTEL Dashboard Restoration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the GM panel "lie detector" by porting ADR-031's three-layer semantic-telemetry contract — fix the broken `just otel` recipe, install translator routing infrastructure, anchor every span under a `turn_span` root, and stand up the Layer-3 narrative-validator pipeline.

**Architecture:** Layer 1 (FastAPI `/ws/watcher`) is unchanged. Layer 2 gets a load-bearing `turn_span()` context manager that opens at every dispatch entry — every other span becomes its child. The translator (`WatcherSpanProcessor.on_end`) gains a `SpanRoute`-driven routing table colocated with span constants in `spans.py` so closing a span emits both the existing `agent_span_close` AND a typed `WatcherEvent` (state_transition, prompt_assembled, lore_retrieval, json_extraction_result). Layer 3 is new: a `TurnRecord` dataclass assembled at dispatch end, queued onto a bounded `asyncio.Queue(32)`, and consumed by a single validator task that runs five deterministic checks and publishes `validation_warning` / `coverage_gap` / `subsystem_exercise_summary` / `turn_complete` events.

**Tech Stack:** Python 3.12, FastAPI/uvicorn, OpenTelemetry SDK (`opentelemetry-sdk`), `asyncio.Queue`, `pytest` + `pytest-asyncio`, `dataclasses`, `blake2b` (hashlib).

**Out of scope for this plan (deferred to follow-up plans, one per emission family):** Phase 2 emission rollouts for narrator, orchestrator, content, trope, barrier, music, persistence, chargen, NPC, creature, disposition, state-patches, merchant, inventory, continuity, compose, world, RAG, script-tool, reminders, pregen, catch-up, scenario, monster-manual. The `turn_span` is the only Phase 2 emission this plan installs because every other span must nest under it.

---

## File Structure

### Modify
- `justfile` — fix `otel` recipe to call `playtest_dashboard.py` instead of the deleted `playtest.py`.
- `sidequest-server/sidequest/telemetry/setup.py` — drop the unconditional `ConsoleSpanExporter`; gate behind `SIDEQUEST_OTEL_CONSOLE=1`.
- `sidequest-server/sidequest/telemetry/spans.py` — add `SpanRoute` dataclass, `FLAT_ONLY_SPANS` set, `SPAN_ROUTES` dict, `turn_span()` helper.
- `sidequest-server/sidequest/server/watcher.py` — refactor `WatcherSpanProcessor.on_end` to consult the router and emit typed events in addition to `agent_span_close`.
- `sidequest-server/sidequest/server/session_handler.py` — open `turn_span()` at dispatch entry; assemble `TurnRecord` and put it on the validator queue at dispatch end.
- `sidequest-server/sidequest/server/app.py` — start the validator task at FastAPI startup; drain on shutdown.
- `sidequest-ui/src/types/watcher.ts` — update header comment to point at the Python source files.
- `docs/adr/031-game-watcher-semantic-telemetry.md` — append a Python-port section; flip implementation-status notes.
- `CLAUDE.md` — regenerate ADR Index block via `scripts/regenerate_adr_indexes.py`.

### Create
- `sidequest-server/sidequest/telemetry/turn_record.py` — `TurnRecord` and `PatchSummary` dataclasses.
- `sidequest-server/sidequest/telemetry/validator.py` — `Validator` class, the five checks, lifecycle hooks, health emissions.
- `sidequest-server/tests/telemetry/test_routing_completeness.py` — static lint that every `SPAN_*` constant is either routed or in `FLAT_ONLY_SPANS`.
- `sidequest-server/tests/telemetry/test_validator_pipeline.py` — lifecycle, backpressure, crash containment, per-check fixtures.
- `sidequest-server/tests/server/test_turn_span_wiring.py` — integration test that the dispatch entry opens `turn` as the root span.
- `docs/adr/089-otel-dashboard-restoration.md` — new ADR, status `accepted`, related `[031, 058, 082]`.
- `.github/workflows/just-otel-smoke.yml` (or extend existing CI workflow) — smoke test for the `just otel` recipe.

### Test
- `sidequest-server/tests/server/test_watcher_events.py` — extend with parametrized translator-routing rows.
- `sidequest-server/tests/telemetry/test_spans.py` — extend with `turn_span()` helper assertions.

**Decomposition rationale:** `turn_record.py` and `validator.py` are split because the dataclass is consumed by both the dispatch hot path and the validator cold path; keeping the queue-side logic separate from the data shape keeps each file under ~250 lines and avoids a circular import between `session_handler` and the validator module. The `SpanRoute` mechanism lives in `spans.py` (not a new file) because the spec requires colocation with the span constants — renaming a constant must break the route at import.

---

## Phase 0 — Stop the Bleed

### Task 1: Fix the `just otel` recipe

**Files:**
- Modify: `justfile:188-190`

- [ ] **Step 1: Inspect the current recipe**

Run: `sed -n '186,192p' justfile`
Expected output includes `python3 {{root}}/scripts/playtest.py --dashboard-only --dashboard-port {{port}}` (the broken line).

- [ ] **Step 2: Update the recipe to call the split-out script**

Edit `justfile:188-190` to:

```just
# OTEL dashboard — browser-friendly /ws/watcher viewer
otel port="9765":
    python3 {{root}}/scripts/playtest_dashboard.py --dashboard-port {{port}}
```

(Drops the `--dashboard-only` flag, which was a `playtest.py` switch and is not a `playtest_dashboard.py` flag.)

- [ ] **Step 3: Verify `playtest_dashboard.py` accepts `--dashboard-port`**

Run: `python3 scripts/playtest_dashboard.py --help`
Expected: argparse output including `--dashboard-port`. If the flag is named differently (e.g. `--port`), update the recipe to match.

- [ ] **Step 4: Smoke-run the recipe locally**

Run: `timeout 3 just otel || [[ $? -eq 124 ]]; echo "exit=$?"`
Expected: `exit=0` (timeout fired = recipe started successfully and is listening).

- [ ] **Step 5: Commit**

```bash
git add justfile
git commit -m "fix(justfile): point otel recipe at playtest_dashboard.py"
```

---

### Task 2: Gate `ConsoleSpanExporter` behind an env var

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/setup.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_setup_gating.py`:

```python
"""Tests that ConsoleSpanExporter is gated behind SIDEQUEST_OTEL_CONSOLE."""

from __future__ import annotations

import os

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


def _has_console_exporter(provider: TracerProvider) -> bool:
    active = getattr(provider, "_active_span_processor", None)
    processors = getattr(active, "_span_processors", ()) if active else ()
    for proc in processors:
        exporter = getattr(proc, "span_exporter", None)
        if isinstance(exporter, ConsoleSpanExporter):
            return True
    return False


def _reset_tracer():
    """Force re-init by clearing the module-level _initialized flag."""
    from sidequest.telemetry import setup as setup_mod

    setup_mod._initialized = False
    # Reset the global provider to a fresh SDK provider so the next init wins.
    trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]


def test_console_exporter_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIDEQUEST_OTEL_CONSOLE", raising=False)
    _reset_tracer()

    from sidequest.telemetry.setup import init_tracer

    init_tracer()
    provider = trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider)
    assert not _has_console_exporter(provider), (
        "ConsoleSpanExporter should be off when SIDEQUEST_OTEL_CONSOLE is unset"
    )


def test_console_exporter_on_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDEQUEST_OTEL_CONSOLE", "1")
    _reset_tracer()

    from sidequest.telemetry.setup import init_tracer

    init_tracer()
    provider = trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider)
    assert _has_console_exporter(provider), (
        "ConsoleSpanExporter should be enabled when SIDEQUEST_OTEL_CONSOLE=1"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_setup_gating.py -v`
Expected: FAIL — `test_console_exporter_off_by_default` fails because the current `setup.py` always installs the console exporter.

- [ ] **Step 3: Implement the gating in `setup.py`**

Replace the body of `sidequest-server/sidequest/telemetry/setup.py` with:

```python
"""OpenTelemetry tracer setup for sidequest-server.

The default destination for spans is the WatcherSpanProcessor (registered
in server/app.py). Console export is debug-only and gated behind
SIDEQUEST_OTEL_CONSOLE=1 so that normal runs don't pollute stdout with
span dumps.
"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

_initialized = False


def init_tracer(service_name: str = "sidequest-server") -> None:
    """Initialize the global OpenTelemetry tracer provider.

    Idempotent — safe to call from tests and from app startup.
    """
    global _initialized
    if _initialized:
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if os.environ.get("SIDEQUEST_OTEL_CONSOLE") == "1":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    _initialized = True


def tracer() -> trace.Tracer:
    """Return the sidequest-server tracer."""
    return trace.get_tracer("sidequest-server")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_setup_gating.py -v`
Expected: PASS — both tests green.

Run: `cd sidequest-server && uv run pytest tests/telemetry/ -v`
Expected: PASS — no regressions in other telemetry tests.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/setup.py tests/telemetry/test_setup_gating.py
git commit -m "feat(telemetry): gate ConsoleSpanExporter behind SIDEQUEST_OTEL_CONSOLE"
```

---

### Task 3: Add CI smoke test for `just otel`

**Files:**
- Create: `.github/workflows/just-otel-smoke.yml` (or extend `ci.yml` if a single workflow file exists)

- [ ] **Step 1: Inspect existing CI layout**

Run: `ls .github/workflows/ 2>&1`
Expected: list of YAML files. If `ci.yml` exists, prefer extending it; otherwise create a dedicated `just-otel-smoke.yml`.

- [ ] **Step 2: Write the smoke job**

If extending an existing workflow, add this job. If creating a new one, the full file:

```yaml
name: just otel smoke

on:
  pull_request:
    paths:
      - "justfile"
      - "scripts/playtest_dashboard.py"
      - ".github/workflows/just-otel-smoke.yml"
  push:
    branches: [main]

jobs:
  just-otel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Install just
        run: |
          curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh \
            | bash -s -- --to /usr/local/bin

      - name: Install Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install playtest deps
        run: |
          pip install -r scripts/requirements-playtest.txt 2>/dev/null || pip install websockets aiohttp

      - name: Smoke-test `just otel`
        run: timeout 5 just otel || [ $? -eq 124 ]
        # exit 124 = timeout fired = recipe started and is listening
```

- [ ] **Step 3: Verify the workflow file is well-formed**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/just-otel-smoke.yml'))"` (or pipe through `yamllint` if available)
Expected: no parse errors.

- [ ] **Step 4: Local dry-run of the smoke command**

Run: `timeout 5 just otel || [ $? -eq 124 ] && echo OK`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/just-otel-smoke.yml
git commit -m "ci: smoke-test the just otel recipe to catch script renames"
```

---

## Phase 1 — Translator Routing Infrastructure

### Task 4: Add `SpanRoute` dataclass and `FLAT_ONLY_SPANS` set

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans.py` (top of file, after imports)

- [ ] **Step 1: Write the failing test**

Add to `sidequest-server/tests/telemetry/test_spans.py`:

```python
def test_span_route_dataclass_shape() -> None:
    """SpanRoute carries event_type, component, and an attribute extractor."""
    from sidequest.telemetry.spans import SpanRoute

    route = SpanRoute(
        event_type="state_transition",
        component="disposition",
        extract=lambda span: {"npc": "alice"},
    )
    assert route.event_type == "state_transition"
    assert route.component == "disposition"
    # The extractor takes a span-like object and returns a dict.
    fake = type("FakeSpan", (), {"attributes": {}, "name": "x"})()
    assert route.extract(fake) == {"npc": "alice"}


def test_flat_only_spans_is_a_set_of_strings() -> None:
    """FLAT_ONLY_SPANS contains span name strings, not SpanRoute objects."""
    from sidequest.telemetry.spans import FLAT_ONLY_SPANS

    assert isinstance(FLAT_ONLY_SPANS, set)
    for name in FLAT_ONLY_SPANS:
        assert isinstance(name, str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_spans.py::test_span_route_dataclass_shape tests/telemetry/test_spans.py::test_flat_only_spans_is_a_set_of_strings -v`
Expected: FAIL — `SpanRoute` and `FLAT_ONLY_SPANS` don't exist yet.

- [ ] **Step 3: Add `SpanRoute` and `FLAT_ONLY_SPANS` to `spans.py`**

Add to the top of `sidequest-server/sidequest/telemetry/spans.py`, immediately after the existing imports:

```python
from dataclasses import dataclass
from typing import Callable, Protocol


class _SpanLike(Protocol):
    """Structural stand-in for opentelemetry.sdk.trace.ReadableSpan."""

    name: str
    attributes: dict[str, Any] | None


@dataclass(frozen=True)
class SpanRoute:
    """Routing decision for a span family.

    The translator consults the SPAN_ROUTES dict keyed by span name. When a
    span closes, if its name is in the dict, the matching SpanRoute is used
    to emit a typed WatcherEvent IN ADDITION TO the always-on
    agent_span_close fan-out. The extractor pulls the typed event's
    `fields` from the span's attributes — span attributes are the single
    source of truth for typed-event payloads.
    """

    event_type: str
    component: str
    extract: Callable[[_SpanLike], dict[str, Any]]


# Spans that intentionally have no typed-event route. Closing one of these
# emits agent_span_close only — they carry timing data but no semantic
# payload the dashboard needs to classify. Membership is a deliberate
# decision, enforced by tests/telemetry/test_routing_completeness.py.
FLAT_ONLY_SPANS: set[str] = set()


# Span name -> SpanRoute. Populated near each SPAN_* constant below so
# that renaming a constant breaks the route at import time, and a new
# constant without a routing decision trips the completeness lint test.
SPAN_ROUTES: dict[str, SpanRoute] = {}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_spans.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/spans.py tests/telemetry/test_spans.py
git commit -m "feat(telemetry): add SpanRoute, SPAN_ROUTES, FLAT_ONLY_SPANS scaffolding"
```

---

### Task 5: Populate `SPAN_ROUTES` and `FLAT_ONLY_SPANS` for currently-emitted spans

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans.py`

This task seeds the routing table with entries for spans that currently emit in production code, so the routing-completeness lint (Task 7) can pass on first run. Spans for the ~24 follow-up emission families will be added in their respective follow-up plans.

- [ ] **Step 1: Identify currently-emitting spans**

Run: `cd sidequest-server && grep -rn "start_as_current_span\|_span(" sidequest/ --include="*.py" | grep -v "telemetry/spans.py" | sed 's/:.*//' | sort -u`
Expected: list of files that open spans. Cross-reference against `SPAN_*` constants in `spans.py` to identify which constants have at least one emission site today.

- [ ] **Step 2: Identify currently-live span constants**

Currently-live spans (verified by the spec §1.2 emission-site count and grep above):

- `SPAN_AGENT_CALL`, `SPAN_AGENT_CALL_SESSION` — agent.call timing
- `SPAN_TURN_AGENT_LLM_INFERENCE` — LLM inference timing
- `SPAN_NPC_AUTO_REGISTERED`, `SPAN_NPC_REINVENTED` — NPC dispatch (story 37-44)
- `SPAN_COMBAT_TICK`, `SPAN_COMBAT_ENDED`, `SPAN_COMBAT_PLAYER_DEAD` — combat dispatch (story 3.4)
- `SPAN_ENCOUNTER_*` family — encounter dispatch (story 3.4)
- `SPAN_LOCAL_DM_DECOMPOSE`, `SPAN_LOCAL_DM_DISPATCH_BANK`, `SPAN_LOCAL_DM_LETHALITY_ARBITRATE`, `SPAN_LOCAL_DM_SUBSYSTEM`
- `SPAN_DICE_REQUEST_SENT`, `SPAN_DICE_THROW_RECEIVED`, `SPAN_DICE_RESULT_BROADCAST`
- `SPAN_PROJECTION_DECIDE`, `SPAN_PROJECTION_CACHE_FILL`, `SPAN_PROJECTION_CACHE_LAZY_FILL`
- `SPAN_LETHALITY_*` (per `test_lethality_span.py`)

If your grep reveals additional live spans, add them.

- [ ] **Step 3: Add routes and flat-only entries inline next to each constant**

For each currently-live span, add either a `SPAN_ROUTES[...] = SpanRoute(...)` entry or a `FLAT_ONLY_SPANS.add(...)` line immediately after the constant's declaration. Example placement pattern:

```python
SPAN_DICE_REQUEST_SENT = "dice.request_sent"
SPAN_ROUTES[SPAN_DICE_REQUEST_SENT] = SpanRoute(
    event_type="state_transition",
    component="dice",
    extract=lambda span: {
        "field": "dice.request",
        "request_id": (span.attributes or {}).get("request_id", ""),
        "expression": (span.attributes or {}).get("expression", ""),
    },
)
```

For timing-only spans:

```python
SPAN_AGENT_CALL = "agent.call"
FLAT_ONLY_SPANS.add(SPAN_AGENT_CALL)
```

Reference table for each currently-live span — apply per spec §6.4:

| Constant | Decision | event_type | component | Notes |
|---|---|---|---|---|
| `SPAN_AGENT_CALL` | flat-only | — | — | Subprocess timing |
| `SPAN_AGENT_CALL_SESSION` | flat-only | — | — | Subprocess timing |
| `SPAN_TURN_AGENT_LLM_INFERENCE` | flat-only | — | — | LLM duration |
| `SPAN_NPC_AUTO_REGISTERED` | route | `state_transition` | `npc_registry` | Extract `npc_name`, `slug` |
| `SPAN_NPC_REINVENTED` | route | `state_transition` | `npc_registry` | Extract `npc_name`, `slug`, `reason` |
| `SPAN_COMBAT_TICK` | route | `state_transition` | `combat` | Extract `tick`, `actor_count` |
| `SPAN_COMBAT_ENDED` | route | `state_transition` | `combat` | Extract `outcome` |
| `SPAN_COMBAT_PLAYER_DEAD` | route | `state_transition` | `combat` | Extract `player_id` |
| `SPAN_ENCOUNTER_PHASE_TRANSITION` | route | `state_transition` | `encounter` | Extract `from_phase`, `to_phase` |
| `SPAN_ENCOUNTER_RESOLVED` | route | `state_transition` | `encounter` | Extract `outcome` |
| `SPAN_ENCOUNTER_BEAT_APPLIED` | route | `state_transition` | `encounter` | Extract `beat`, `actor` |
| `SPAN_ENCOUNTER_CONFRONTATION_INITIATED` | route | `state_transition` | `encounter` | Extract `confrontation_kind` |
| `SPAN_ENCOUNTER_EMPTY_ACTOR_LIST` | route | `state_transition` | `encounter` | Extract `phase` |
| `SPAN_ENCOUNTER_BEAT_FAILURE_BRANCH` | route | `state_transition` | `encounter` | Extract `beat`, `branch` |
| `SPAN_LOCAL_DM_DECOMPOSE` | route | `state_transition` | `local_dm` | Extract `intent`, `branch` |
| `SPAN_LOCAL_DM_DISPATCH_BANK` | route | `state_transition` | `local_dm` | Extract `bank`, `dispatched_to` |
| `SPAN_LOCAL_DM_LETHALITY_ARBITRATE` | route | `state_transition` | `local_dm` | Extract `verdict`, `inputs` |
| `SPAN_LOCAL_DM_SUBSYSTEM` | route | `subsystem_exercise_summary` | `local_dm` | Extract `subsystem`, `exercised` |
| `SPAN_DICE_REQUEST_SENT` | route | `state_transition` | `dice` | Extract `request_id`, `expression` |
| `SPAN_DICE_THROW_RECEIVED` | route | `state_transition` | `dice` | Extract `request_id`, `result` |
| `SPAN_DICE_RESULT_BROADCAST` | route | `state_transition` | `dice` | Extract `request_id`, `players` |
| `SPAN_PROJECTION_DECIDE` | route | `state_transition` | `projection` | Extract `player_id`, `decision` |
| `SPAN_PROJECTION_CACHE_FILL` | route | `state_transition` | `projection` | Extract `player_id`, `keys` |
| `SPAN_PROJECTION_CACHE_LAZY_FILL` | route | `state_transition` | `projection` | Extract `player_id`, `keys` |

The `extract` lambdas always defensively coerce `span.attributes or {}` because `ReadableSpan.attributes` can be `None`. Match attribute names to whatever the existing emission sites set — open the file that calls `.start_as_current_span(SPAN_X, attributes={...})` and copy the keys verbatim.

- [ ] **Step 4: Run all telemetry tests**

Run: `cd sidequest-server && uv run pytest tests/telemetry/ -v`
Expected: PASS — no regressions. Routing-completeness test doesn't exist yet (Task 7), so this only verifies existing tests still pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/spans.py
git commit -m "feat(telemetry): seed SPAN_ROUTES and FLAT_ONLY_SPANS for live spans"
```

---

### Task 6: Refactor `WatcherSpanProcessor.on_end` to use the router

**Files:**
- Modify: `sidequest-server/sidequest/server/watcher.py:64-86`

- [ ] **Step 1: Write the failing test**

Add to `sidequest-server/tests/server/test_watcher_events.py` (extend existing file):

```python
import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanContext, Status, StatusCode, TraceFlags

from sidequest.server.watcher import WatcherSpanProcessor
from sidequest.telemetry import spans as spans_mod
from sidequest.telemetry.spans import SPAN_DICE_REQUEST_SENT
from sidequest.telemetry.watcher_hub import WatcherHub


def _fake_span(
    name: str,
    attributes: dict | None = None,
    status_code: StatusCode = StatusCode.OK,
) -> ReadableSpan:
    """Build a ReadableSpan stand-in for tests."""
    span = MagicMock(spec=ReadableSpan)
    span.name = name
    span.attributes = attributes or {}
    span.start_time = 1_000_000_000
    span.end_time = 2_000_000_000
    span.status = MagicMock()
    span.status.status_code = MagicMock()
    span.status.status_code.name = "OK" if status_code == StatusCode.OK else "ERROR"
    return span


class _CapturingSubscriber:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def send_json(self, data: dict) -> None:
        self.events.append(data)


@pytest.mark.asyncio
async def test_on_end_emits_agent_span_close_for_every_span() -> None:
    """Backward-compat: every closed span still produces agent_span_close."""
    hub = WatcherHub()
    hub.bind_loop(asyncio.get_running_loop())
    sub = _CapturingSubscriber()
    await hub.subscribe(sub)

    processor = WatcherSpanProcessor(hub)
    processor.on_end(_fake_span("some.untracked.span", {"a": 1}))

    # Allow the cross-thread coroutine hop to flush.
    await asyncio.sleep(0.05)

    assert any(e["event_type"] == "agent_span_close" for e in sub.events)


@pytest.mark.asyncio
async def test_on_end_emits_typed_event_for_routed_span() -> None:
    """When a span name is in SPAN_ROUTES, on_end ALSO emits the typed event."""
    hub = WatcherHub()
    hub.bind_loop(asyncio.get_running_loop())
    sub = _CapturingSubscriber()
    await hub.subscribe(sub)

    processor = WatcherSpanProcessor(hub)
    processor.on_end(_fake_span(
        SPAN_DICE_REQUEST_SENT,
        {"request_id": "r1", "expression": "1d20"},
    ))
    await asyncio.sleep(0.05)

    typed = [e for e in sub.events if e["event_type"] == "state_transition"]
    flat = [e for e in sub.events if e["event_type"] == "agent_span_close"]
    assert typed, "Routed span did not produce a typed state_transition event"
    assert flat, "Routed span must STILL produce agent_span_close (augment, not replace)"
    assert typed[0]["component"] == "dice"
    assert typed[0]["fields"]["request_id"] == "r1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_watcher_events.py::test_on_end_emits_typed_event_for_routed_span -v`
Expected: FAIL — current `on_end` only emits `agent_span_close`.

- [ ] **Step 3: Refactor `on_end`**

Replace `WatcherSpanProcessor.on_end` in `sidequest-server/sidequest/server/watcher.py` with:

```python
def on_end(self, span: ReadableSpan) -> None:
    end_ns = span.end_time or 0
    start_ns = span.start_time or end_ns
    duration_ms = max(0, (end_ns - start_ns) // 1_000_000)
    attrs: dict[str, Any] = {}
    if span.attributes:
        for k, v in span.attributes.items():
            attrs[str(k)] = v

    severity = "info"
    if span.status is not None and span.status.status_code.name == "ERROR":
        severity = "error"

    # Always emit the flat firehose event — Timeline / Timing tabs depend on it.
    self._hub.publish(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "component": "sidequest-server",
            "event_type": "agent_span_close",
            "severity": severity,
            "fields": {
                "name": span.name,
                "duration_ms": duration_ms,
                **attrs,
            },
        }
    )

    # Then, if the span has a routing decision, emit the typed event too.
    from sidequest.telemetry.spans import SPAN_ROUTES

    route = SPAN_ROUTES.get(span.name)
    if route is None:
        return

    try:
        fields = route.extract(span)
    except Exception as exc:  # noqa: BLE001
        # Per CLAUDE.md: no silent fallbacks. Surface the failure on the bus
        # so the operator sees that the translator is broken, not silently
        # missing typed events.
        logger.exception("watcher.route_extract_failed span=%s", span.name)
        self._hub.publish(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "component": "watcher",
                "event_type": "validation_warning",
                "severity": "error",
                "fields": {
                    "check": "route_extract",
                    "span": span.name,
                    "error": str(exc),
                },
            }
        )
        return

    # Inferred severity per spec §6.5.
    typed_severity = severity
    if route.event_type == "json_extraction_result":
        tier = fields.get("tier")
        if isinstance(tier, int) and tier > 1:
            typed_severity = "warning"

    self._hub.publish(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "component": route.component,
            "event_type": route.event_type,
            "severity": typed_severity,
            "fields": fields,
        }
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_watcher_events.py -v`
Expected: PASS — both new tests green; existing tests still green.

Run: `cd sidequest-server && uv run pytest tests/server/ -v -x`
Expected: PASS — no regressions.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/server/watcher.py tests/server/test_watcher_events.py
git commit -m "feat(watcher): translator emits typed events via SPAN_ROUTES on close"
```

---

### Task 7: Add the routing-completeness lint test

**Files:**
- Create: `sidequest-server/tests/telemetry/test_routing_completeness.py`

- [ ] **Step 1: Write the test**

Create `sidequest-server/tests/telemetry/test_routing_completeness.py`:

```python
"""Static lint: every SPAN_* constant must have a routing decision.

A new span constant added to spans.py without either an entry in
SPAN_ROUTES or membership in FLAT_ONLY_SPANS is a routing gap — the
translator will emit only agent_span_close, and the dashboard's typed
tabs will silently miss the new subsystem. This test forces the
decision to be explicit at the point a constant is introduced.
"""

from __future__ import annotations

from sidequest.telemetry import spans
from sidequest.telemetry.spans import FLAT_ONLY_SPANS, SPAN_ROUTES


def _all_span_constants() -> set[str]:
    """Every SPAN_* attribute on the spans module that holds a string."""
    return {
        v
        for name, v in vars(spans).items()
        if name.startswith("SPAN_") and isinstance(v, str)
    }


def test_every_span_is_routed_or_explicitly_flat() -> None:
    all_spans = _all_span_constants()
    routed = set(SPAN_ROUTES.keys())
    flat = set(FLAT_ONLY_SPANS)
    missing = all_spans - routed - flat
    overlap = routed & flat

    assert not overlap, (
        f"Spans cannot be both routed AND flat-only: {sorted(overlap)}"
    )
    assert not missing, (
        "Spans without a routing decision (add to SPAN_ROUTES or "
        f"FLAT_ONLY_SPANS): {sorted(missing)}"
    )


def test_routes_target_known_event_types() -> None:
    """Each SpanRoute.event_type matches a WatcherEventType the dashboard
    handles. This is a string check — the source of truth is
    sidequest-ui/src/types/watcher.ts."""
    known = {
        "agent_span_open",
        "agent_span_close",
        "state_transition",
        "turn_complete",
        "lore_retrieval",
        "prompt_assembled",
        "game_state_snapshot",
        "validation_warning",
        "subsystem_exercise_summary",
        "coverage_gap",
        "json_extraction_result",
    }
    bad = [
        (name, route.event_type)
        for name, route in SPAN_ROUTES.items()
        if route.event_type not in known
    ]
    assert not bad, f"Routes targeting unknown event types: {bad}"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_routing_completeness.py -v`
Expected: PASS — every currently-live `SPAN_*` constant has a decision from Task 5.

If FAIL: the failure message lists missing constants; go back to Task 5 and add them to either `SPAN_ROUTES` or `FLAT_ONLY_SPANS`.

- [ ] **Step 3: Verify it actually catches missing routes**

Sanity check: temporarily add `SPAN_TEST_SENTINEL = "test.sentinel"` to `spans.py`, re-run:

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_routing_completeness.py -v`
Expected: FAIL — sentinel listed in missing.

Remove the sentinel and re-run:
Expected: PASS.

- [ ] **Step 4: No-op (lint test only)**

This task has no implementation step — the test IS the deliverable.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add tests/telemetry/test_routing_completeness.py
git commit -m "test(telemetry): lint every SPAN_* constant has a routing decision"
```

---

## Phase 2 — Turn Root Span (Load-Bearing)

This is the only Phase 2 emission included in this plan. Every other emission family from spec §4.1 is a follow-up plan.

### Task 8: Add `turn_span()` context-manager helper

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans.py`

- [ ] **Step 1: Write the failing test**

Add to `sidequest-server/tests/telemetry/test_spans.py`:

```python
def test_turn_span_opens_named_span_with_required_attrs() -> None:
    """turn_span() yields a span named 'turn' with required attributes set."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from sidequest.telemetry.spans import SPAN_TURN, turn_span

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    with turn_span(
        turn_id=42,
        player_id="alice",
        agent_name="narrator",
    ):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == SPAN_TURN
    attrs = dict(spans[0].attributes or {})
    assert attrs["turn_id"] == 42
    assert attrs["player_id"] == "alice"
    assert attrs["agent_name"] == "narrator"


def test_turn_span_accepts_extra_attrs() -> None:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from sidequest.telemetry.spans import turn_span

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    with turn_span(
        turn_id=1,
        player_id="bob",
        agent_name="narrator",
        room_id="room-7",
        extraction_tier=1,
    ):
        pass

    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs["room_id"] == "room-7"
    assert attrs["extraction_tier"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_spans.py::test_turn_span_opens_named_span_with_required_attrs -v`
Expected: FAIL — `turn_span` does not exist in `spans.py`.

- [ ] **Step 3: Add the helper to `spans.py`**

In `sidequest-server/sidequest/telemetry/spans.py`, locate the section starting `# Turn — sidequest-server/dispatch/mod.rs, dispatch/tropes.rs` and immediately after the `SPAN_TURN_*` constants, add:

```python
@contextmanager
def turn_span(
    *,
    turn_id: int,
    player_id: str,
    agent_name: str,
    **attrs: Any,
) -> Iterator[trace.Span]:
    """Open the root `turn` span for a dispatch.

    Every other span opened during this dispatch becomes a child of this
    span. Without it, traces are orphaned — the Timing tab cannot group by
    turn and the Subsystems tab cannot derive per-turn exercise summaries.

    Required attributes match ADR-031 §"Layer 2" turn-root contract:
    turn_id, player_id, agent_name. Extras are accepted via **attrs and
    set on the span verbatim.
    """
    with tracer().start_as_current_span(SPAN_TURN) as span:
        span.set_attribute("turn_id", turn_id)
        span.set_attribute("player_id", player_id)
        span.set_attribute("agent_name", agent_name)
        for k, v in attrs.items():
            span.set_attribute(k, v)
        yield span
```

Also add the routing decision below the existing `SPAN_TURN` constant (the validator owns `turn_complete`, so the root span itself is flat-only):

```python
FLAT_ONLY_SPANS.add(SPAN_TURN)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_spans.py -v`
Expected: PASS.

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_routing_completeness.py -v`
Expected: PASS — `SPAN_TURN` is now in `FLAT_ONLY_SPANS`.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/spans.py tests/telemetry/test_spans.py
git commit -m "feat(telemetry): add turn_span() root context manager"
```

---

### Task 9: Open `turn_span()` at the dispatch entry

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py`

- [ ] **Step 1: Identify the dispatch entry point**

Run: `cd sidequest-server && grep -n "async def \|def handle_action\|def dispatch_action\|class WebSocketSessionHandler" sidequest/server/session_handler.py | head -30`
Expected: locate the top-level coroutine that processes a player action — the function that fires once per turn from the WebSocket route. The spec calls it `session_handler.handle_action`; verify the actual name.

- [ ] **Step 2: Write the wiring test**

Create `sidequest-server/tests/server/test_turn_span_wiring.py`:

```python
"""Wiring test: dispatching an action opens the turn root span."""

from __future__ import annotations

import asyncio

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


@pytest.fixture
def in_memory_exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    # Force re-init so the span helpers pick up the new provider.
    from sidequest.telemetry import setup as setup_mod

    setup_mod._initialized = True
    yield exporter
    exporter.clear()


@pytest.mark.asyncio
async def test_dispatch_opens_turn_span(in_memory_exporter, server_fixture) -> None:
    """A turn dispatch produces at least one span named 'turn'.

    Sister spans opened during the dispatch must appear as children — i.e.
    the parent_span_id of every non-turn span equals the span_id of a 'turn'
    span. This is the load-bearing invariant for the Timing tab's
    "subsystems exercised this turn" grouping.
    """
    await server_fixture.dispatch_action(
        player="alice",
        text="I look around.",
    )

    spans = in_memory_exporter.get_finished_spans()
    turn_spans = [s for s in spans if s.name == "turn"]
    assert turn_spans, "No 'turn' span opened during dispatch"

    turn_span_ids = {s.context.span_id for s in turn_spans}
    non_turn = [s for s in spans if s.name != "turn"]
    if non_turn:
        # Every non-turn span recorded during this dispatch should chain
        # up to one of the turn span IDs (parent or ancestor).
        roots = {s for s in non_turn if s.parent is None}
        assert not roots, (
            f"Non-turn spans without a turn parent (orphans): "
            f"{[r.name for r in roots]}"
        )
```

The `server_fixture` is the existing dispatch fixture; if a different fixture name is used in the codebase, swap it in. If no equivalent fixture exists, build the minimal one inline:

```python
@pytest.fixture
async def server_fixture():
    from sidequest.server.app import create_app
    # Minimal in-memory app for dispatch testing; adapt to the project's
    # existing pattern in tests/server/conftest.py.
    ...
```

Check `tests/server/conftest.py` for the canonical dispatch fixture and reuse it.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_turn_span_wiring.py -v`
Expected: FAIL — no `turn` span is opened by dispatch yet.

- [ ] **Step 4: Wrap the dispatch entry in `turn_span()`**

In `sidequest-server/sidequest/server/session_handler.py`, identify the dispatch coroutine (located in Step 1). Wrap its body in `turn_span()`. Concretely:

```python
# At the top of session_handler.py, ensure this import exists:
from sidequest.telemetry.spans import turn_span

# ... inside the dispatch coroutine (e.g. handle_action) ...
async def handle_action(self, player_id: str, text: str, ...) -> ...:
    turn_id = self._next_turn_id()  # whatever the existing counter is
    agent_name = self._classify_agent(text)  # whatever the existing routing is
    with turn_span(
        turn_id=turn_id,
        player_id=player_id,
        agent_name=agent_name,
    ):
        # All existing dispatch logic moves INSIDE this with-block,
        # unchanged.
        ...
```

The `turn_id` source: use the existing turn counter that the protocol delta already references. The `agent_name`: whatever the dispatch already knows about which subsystem is handling the action — fall back to `"unknown"` if routing happens deeper.

If the dispatch coroutine is large, the entry-and-exit can use the context manager via `async with` if the helper is async — but `turn_span` here is sync, so the `with` form goes around the entire dispatch body.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_turn_span_wiring.py -v`
Expected: PASS.

Run: `cd sidequest-server && uv run pytest tests/server/ tests/telemetry/ -v -x`
Expected: PASS — no regressions across the dispatch and telemetry test suites.

Commit:

```bash
cd sidequest-server
git add sidequest/server/session_handler.py tests/server/test_turn_span_wiring.py
git commit -m "feat(server): open turn_span at dispatch entry to anchor traces"
```

---

## Phase 3 — Validator Pipeline

### Task 10: Create `TurnRecord` and `PatchSummary` dataclasses

**Files:**
- Create: `sidequest-server/sidequest/telemetry/turn_record.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_turn_record.py`:

```python
"""Tests for TurnRecord dataclass shape and immutability."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from sidequest.telemetry.turn_record import PatchSummary, TurnRecord


def _stub_snapshot():
    """Minimal stand-in for GameSnapshot — TurnRecord just holds it."""
    return object()


def _stub_delta():
    return object()


def test_turn_record_is_frozen() -> None:
    record = TurnRecord(
        turn_id=1,
        timestamp=datetime.now(UTC),
        player_id="alice",
        player_input="I look.",
        classified_intent="look",
        agent_name="narrator",
        narration="The room is dark.",
        patches_applied=[],
        snapshot_before_hash="abc",
        snapshot_after=_stub_snapshot(),
        delta=_stub_delta(),
        beats_fired=[],
        extraction_tier=1,
        token_count_in=10,
        token_count_out=20,
        agent_duration_ms=300,
        is_degraded=False,
    )
    with pytest.raises(FrozenInstanceError):
        record.turn_id = 2  # type: ignore[misc]


def test_patch_summary_is_frozen() -> None:
    p = PatchSummary(patch_type="world", fields_changed=["location"])
    with pytest.raises(FrozenInstanceError):
        p.patch_type = "combat"  # type: ignore[misc]


def test_turn_record_carries_all_fields() -> None:
    """All fields per spec §5.1 are present and accessible."""
    record = TurnRecord(
        turn_id=42,
        timestamp=datetime.now(UTC),
        player_id="alice",
        player_input="I attack the troll.",
        classified_intent="combat.attack",
        agent_name="combat",
        narration="You swing.",
        patches_applied=[
            PatchSummary(patch_type="combat", fields_changed=["hp"]),
        ],
        snapshot_before_hash="hash1",
        snapshot_after=_stub_snapshot(),
        delta=_stub_delta(),
        beats_fired=[("desperation", 0.7)],
        extraction_tier=2,
        token_count_in=120,
        token_count_out=240,
        agent_duration_ms=812,
        is_degraded=False,
    )
    assert record.turn_id == 42
    assert record.beats_fired == [("desperation", 0.7)]
    assert record.patches_applied[0].patch_type == "combat"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_turn_record.py -v`
Expected: FAIL — `turn_record` module doesn't exist.

- [ ] **Step 3: Implement the dataclasses**

Create `sidequest-server/sidequest/telemetry/turn_record.py`:

```python
"""TurnRecord — immutable snapshot of a completed dispatch turn.

Assembled at the end of session_handler.handle_action and put on the
validator queue. Frozen for immutability across the queue boundary
(asyncio doesn't enforce isolation; the dataclass does).

Per ADR-089 §2.1 (deliberate departure from Rust ADR-031), Python stores
snapshot_before_hash + snapshot_after + delta rather than two full
GameSnapshot clones — same validation power without the double-clone
cost on every turn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PatchSummary:
    """Compact record of one patch applied during a turn.

    The full patch lives in the snapshot_after via its delta; this
    summary is what the validator's patch_legality_check inspects.
    """

    patch_type: str  # "world" | "combat" | "chase" | "scenario"
    fields_changed: list[str]


@dataclass(frozen=True)
class TurnRecord:
    """One completed turn, ready for narrative validation."""

    turn_id: int
    timestamp: datetime
    player_id: str
    player_input: str
    classified_intent: str
    agent_name: str
    narration: str
    patches_applied: list[PatchSummary]
    snapshot_before_hash: str
    snapshot_after: Any  # GameSnapshot — typed Any to avoid game-layer dep
    delta: Any  # StateDelta — same reason
    beats_fired: list[tuple[str, float]]  # (trope_name, threshold)
    extraction_tier: int  # 1, 2, or 3
    token_count_in: int
    token_count_out: int
    agent_duration_ms: int
    is_degraded: bool
```

The `snapshot_after` and `delta` fields are typed `Any` rather than the concrete `GameSnapshot` / `StateDelta` types to keep `sidequest.telemetry` free of `sidequest.game` imports — same reasoning as `watcher_hub.py` keeping itself FastAPI-free.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_turn_record.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/turn_record.py tests/telemetry/test_turn_record.py
git commit -m "feat(telemetry): TurnRecord and PatchSummary dataclasses"
```

---

### Task 11: Validator skeleton with bounded asyncio.Queue

**Files:**
- Create: `sidequest-server/sidequest/telemetry/validator.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_validator_pipeline.py`:

```python
"""Tests for the Layer-3 narrative validator pipeline."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from sidequest.telemetry.turn_record import PatchSummary, TurnRecord
from sidequest.telemetry.validator import Validator


def _make_record(turn_id: int = 1) -> TurnRecord:
    return TurnRecord(
        turn_id=turn_id,
        timestamp=datetime.now(UTC),
        player_id="alice",
        player_input="I look.",
        classified_intent="look",
        agent_name="narrator",
        narration="The room is dark.",
        patches_applied=[],
        snapshot_before_hash="h0",
        snapshot_after=object(),
        delta=object(),
        beats_fired=[],
        extraction_tier=1,
        token_count_in=10,
        token_count_out=20,
        agent_duration_ms=100,
        is_degraded=False,
    )


@pytest.mark.asyncio
async def test_validator_starts_and_drains_on_shutdown() -> None:
    v = Validator()
    await v.start()
    assert v.is_running()

    await v.submit(_make_record(turn_id=1))
    await v.shutdown(grace_seconds=2.0)

    assert not v.is_running()


@pytest.mark.asyncio
async def test_submit_drops_oldest_under_backpressure() -> None:
    v = Validator(queue_maxsize=2)
    # Don't start the consumer — let the queue fill.
    for i in range(5):
        await v.submit(_make_record(turn_id=i))

    assert v.dropped_records >= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py::test_validator_starts_and_drains_on_shutdown -v`
Expected: FAIL — `validator` module doesn't exist.

- [ ] **Step 3: Implement the Validator skeleton**

Create `sidequest-server/sidequest/telemetry/validator.py`:

```python
"""Layer-3 narrative validator — consumes TurnRecord, emits typed events.

Lifecycle: started by FastAPI's startup event, drained on shutdown.
A single asyncio.Task processes one TurnRecord at a time; the queue is
bounded and oldest-record-drops on QueueFull (faithful to ADR-031's
"lossy by design" intent).

The validator never raises into the dispatch hot path. Each check is
wrapped in try/except — a check exception fires a validation_warning
with severity=error rather than crashing the task. If the task itself
dies, app.py's startup hook restarts it on next request (best-effort).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Awaitable, Callable

from sidequest.telemetry.turn_record import TurnRecord
from sidequest.telemetry.watcher_hub import publish_event

logger = logging.getLogger(__name__)

CheckFn = Callable[[TurnRecord], Awaitable[None]]


class Validator:
    """Single-consumer narrative validator pipeline."""

    def __init__(self, queue_maxsize: int = 32) -> None:
        self._queue: asyncio.Queue[TurnRecord] = asyncio.Queue(
            maxsize=queue_maxsize
        )
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._checks: list[CheckFn] = []
        # Health counters
        self.dropped_records: int = 0
        self._check_durations_ms: deque[tuple[str, float]] = deque(maxlen=200)

    def register_check(self, fn: CheckFn) -> None:
        """Register a check coroutine. Called once per TurnRecord."""
        self._checks.append(fn)

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def submit(self, record: TurnRecord) -> None:
        """Enqueue a record. On QueueFull, drop the oldest record."""
        try:
            self._queue.put_nowait(record)
        except asyncio.QueueFull:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
                self.dropped_records += 1
                publish_event(
                    "validation_warning",
                    {
                        "check": "validator.queue",
                        "reason": "queue_full",
                        "dropped_total": self.dropped_records,
                    },
                    component="validator",
                    severity="warning",
                )
            except asyncio.QueueEmpty:
                pass
            try:
                self._queue.put_nowait(record)
            except asyncio.QueueFull:
                self.dropped_records += 1

    async def start(self) -> None:
        if self.is_running():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(
            self._run(), name="sidequest.validator"
        )
        logger.info("validator.started")

    async def shutdown(self, grace_seconds: float = 2.0) -> None:
        self._stopping.set()
        if self._task is None:
            return
        # Drain remaining records up to the grace window.
        try:
            await asyncio.wait_for(
                self._queue.join(), timeout=grace_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(
                "validator.shutdown_grace_exceeded queued=%d",
                self._queue.qsize(),
            )
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("validator.stopped")

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                record = await asyncio.wait_for(
                    self._queue.get(), timeout=0.5
                )
            except asyncio.TimeoutError:
                continue
            try:
                await self._validate(record)
            finally:
                self._queue.task_done()

    async def _validate(self, record: TurnRecord) -> None:
        for check in self._checks:
            t0 = time.perf_counter()
            try:
                await check(record)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "validator.check_failed check=%s", check.__name__
                )
                publish_event(
                    "validation_warning",
                    {
                        "check": check.__name__,
                        "error": str(exc),
                        "turn_id": record.turn_id,
                    },
                    component="validator",
                    severity="error",
                )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self._check_durations_ms.append(
                (check.__name__, elapsed_ms)
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py -v`
Expected: PASS — both lifecycle tests green.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/validator.py tests/telemetry/test_validator_pipeline.py
git commit -m "feat(telemetry): Validator skeleton with bounded queue and lifecycle"
```

---

### Task 12: Implement `entity_check`

Each of Tasks 12–17 implements one of the five checks. They share a fixture pattern.

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/validator.py`
- Modify: `sidequest-server/tests/telemetry/test_validator_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add to `sidequest-server/tests/telemetry/test_validator_pipeline.py`:

```python
from sidequest.telemetry.validator import entity_check
from sidequest.telemetry import watcher_hub as wh_mod


class _CapturedEvents(list):
    pass


@pytest.fixture
def captured_events(monkeypatch):
    captured = _CapturedEvents()

    def fake_publish(event_type, fields, *, component="sidequest-server", severity="info"):
        captured.append({
            "event_type": event_type,
            "fields": fields,
            "component": component,
            "severity": severity,
        })

    monkeypatch.setattr(
        "sidequest.telemetry.validator.publish_event",
        fake_publish,
    )
    return captured


@pytest.mark.asyncio
async def test_entity_check_warns_on_unknown_npc(captured_events) -> None:
    """Narration mentioning an NPC not in the registry produces a
    validation_warning."""
    snapshot_after = type(
        "Snap",
        (),
        {
            "npc_registry": {},  # empty
            "discovered_regions": [],
            "inventory": type("Inv", (), {"items": []})(),
        },
    )()

    record = _make_record()
    record_dict = record.__dict__.copy()
    record_dict["narration"] = "Sir Reginald nods grimly."
    record_dict["snapshot_after"] = snapshot_after
    new_record = TurnRecord(**record_dict)

    await entity_check(new_record)

    warnings = [e for e in captured_events if e["event_type"] == "validation_warning"]
    assert warnings, "entity_check should warn on unknown NPC"
    assert "Sir Reginald" in str(warnings[0]["fields"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py::test_entity_check_warns_on_unknown_npc -v`
Expected: FAIL — `entity_check` does not exist.

- [ ] **Step 3: Implement `entity_check`**

Add to `sidequest-server/sidequest/telemetry/validator.py`:

```python
import re

# Capitalized two-word noun phrases — heuristic for "named entity in
# narration." Matches "Sir Reginald", "The Ironwood", "Lady Ashes" etc.
# False positives are fine — entity_check is a hint, not an oracle.
_NAMED_ENTITY_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")


async def entity_check(record: TurnRecord) -> None:
    """Warn when narration names an NPC / region / item absent from the
    snapshot.

    Reads:
      - narration
      - snapshot_after.npc_registry (mapping name -> NpcRegistryEntry)
      - snapshot_after.discovered_regions (iterable of region names)
      - snapshot_after.inventory.items (iterable of item names)
    """
    snap = record.snapshot_after
    known_names: set[str] = set()
    npc_registry = getattr(snap, "npc_registry", None) or {}
    if isinstance(npc_registry, dict):
        known_names.update(npc_registry.keys())
    regions = getattr(snap, "discovered_regions", None) or ()
    known_names.update(str(r) for r in regions)
    inventory = getattr(snap, "inventory", None)
    if inventory is not None:
        items = getattr(inventory, "items", None) or ()
        for it in items:
            name = getattr(it, "name", None) or str(it)
            known_names.add(name)

    if not record.narration:
        return

    for match in _NAMED_ENTITY_RE.finditer(record.narration):
        candidate = match.group(1)
        if candidate not in known_names:
            publish_event(
                "validation_warning",
                {
                    "check": "entity",
                    "turn_id": record.turn_id,
                    "candidate": candidate,
                    "rationale": "narration names an entity not in snapshot",
                },
                component="validator",
                severity="warning",
            )
            # One warning per turn is sufficient; don't spam.
            return
```

Then register the check in `Validator.__init__` after `self._check_durations_ms` is initialized:

```python
        # Default check registration. Test code can register additional
        # or replacement checks before start().
        self.register_check(entity_check)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py -v`
Expected: PASS — entity_check warns; existing lifecycle tests still pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/validator.py tests/telemetry/test_validator_pipeline.py
git commit -m "feat(validator): entity_check warns on narration of unknown entities"
```

---

### Task 13: Implement `inventory_check`

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/validator.py`
- Modify: `sidequest-server/tests/telemetry/test_validator_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add to the test file:

```python
from sidequest.telemetry.validator import inventory_check


@pytest.mark.asyncio
async def test_inventory_check_warns_on_narration_grab_with_no_patch(
    captured_events,
) -> None:
    """Narration says 'you grab the lantern' but no patch added 'lantern'."""
    record_dict = _make_record().__dict__.copy()
    record_dict["narration"] = "You grab the lantern from the shelf."
    record_dict["patches_applied"] = []  # nothing added
    record_dict["delta"] = type("Delta", (), {"inventory_changes": []})()
    record = TurnRecord(**record_dict)

    await inventory_check(record)
    warnings = [e for e in captured_events if e["event_type"] == "validation_warning"]
    assert any("inventory" in str(w["fields"]) for w in warnings)


@pytest.mark.asyncio
async def test_inventory_check_warns_on_silent_patch(captured_events) -> None:
    """Patch added 'rope' but narration is silent on it."""
    record_dict = _make_record().__dict__.copy()
    record_dict["narration"] = "You walk forward."
    record_dict["patches_applied"] = [
        PatchSummary(patch_type="world", fields_changed=["inventory.rope"]),
    ]
    record_dict["delta"] = type(
        "Delta",
        (),
        {"inventory_changes": [{"item": "rope", "delta": 1}]},
    )()
    record = TurnRecord(**record_dict)

    await inventory_check(record)
    warnings = [e for e in captured_events if e["event_type"] == "validation_warning"]
    assert any("rope" in str(w["fields"]) for w in warnings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py::test_inventory_check_warns_on_narration_grab_with_no_patch -v`
Expected: FAIL.

- [ ] **Step 3: Implement `inventory_check`**

Add to `validator.py`:

```python
_GRAB_VERBS = (
    "grab", "take", "pick up", "pocket", "stash", "loot",
    "snatch", "scoop", "lift", "claim",
)


async def inventory_check(record: TurnRecord) -> None:
    """Cross-check narration against inventory deltas.

    Two failure modes:
      1. Narration uses a grab-verb but no patch added inventory.
      2. A patch added an item but narration doesn't mention it.
    """
    narration = (record.narration or "").lower()
    delta = record.delta
    inv_changes = getattr(delta, "inventory_changes", None) or []
    has_inventory_patch = bool(inv_changes) or any(
        any("inventory" in f for f in p.fields_changed)
        for p in record.patches_applied
    )

    grabbed_in_narration = any(v in narration for v in _GRAB_VERBS)

    if grabbed_in_narration and not has_inventory_patch:
        publish_event(
            "validation_warning",
            {
                "check": "inventory",
                "turn_id": record.turn_id,
                "rationale": "narration describes a grab but no inventory patch",
            },
            component="validator",
            severity="warning",
        )

    # Patch added an item, narration silent on it.
    for change in inv_changes:
        item = change.get("item") if isinstance(change, dict) else getattr(change, "item", None)
        if not item:
            continue
        if str(item).lower() not in narration:
            publish_event(
                "validation_warning",
                {
                    "check": "inventory",
                    "turn_id": record.turn_id,
                    "item": item,
                    "rationale": "patch added item but narration is silent",
                },
                component="validator",
                severity="warning",
            )
```

Register the check in `Validator.__init__` alongside `entity_check`:

```python
        self.register_check(entity_check)
        self.register_check(inventory_check)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/validator.py tests/telemetry/test_validator_pipeline.py
git commit -m "feat(validator): inventory_check warns on narration/patch mismatches"
```

---

### Task 14: Implement `patch_legality_check`

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/validator.py`
- Modify: `sidequest-server/tests/telemetry/test_validator_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
from sidequest.telemetry.validator import patch_legality_check


@pytest.mark.asyncio
async def test_patch_legality_warns_on_hp_over_max(captured_events) -> None:
    """HP > max in snapshot_after is an illegal patch outcome."""

    class _Char:
        def __init__(self, hp: int, hp_max: int) -> None:
            self.hp = hp
            self.hp_max = hp_max

    snapshot_after = type(
        "Snap",
        (),
        {
            "characters": {"alice": _Char(hp=120, hp_max=100)},
            "npc_registry": {},
        },
    )()
    record_dict = _make_record().__dict__.copy()
    record_dict["snapshot_after"] = snapshot_after
    record_dict["patches_applied"] = [
        PatchSummary(patch_type="combat", fields_changed=["characters.alice.hp"]),
    ]
    record = TurnRecord(**record_dict)

    await patch_legality_check(record)
    errors = [
        e for e in captured_events
        if e["event_type"] == "validation_warning" and e["severity"] == "error"
    ]
    assert errors, "HP-over-max should produce an error-severity warning"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py::test_patch_legality_warns_on_hp_over_max -v`
Expected: FAIL.

- [ ] **Step 3: Implement `patch_legality_check`**

Add to `validator.py`:

```python
async def patch_legality_check(record: TurnRecord) -> None:
    """Detect illegal post-patch state.

    Checks (per ADR-031 §"Patch legality"):
      - HP > max for any character or NPC
      - Dead NPC (hp <= 0) appears in patches_applied as an actor
      - (Cartography graph adjacency check is deferred until the
        cartography graph is ported — see ADR-019.)
    """
    snap = record.snapshot_after
    characters = getattr(snap, "characters", None) or {}
    npc_registry = getattr(snap, "npc_registry", None) or {}

    def _check_hp(label: str, owner: str, ch: object) -> None:
        hp = getattr(ch, "hp", None)
        hp_max = getattr(ch, "hp_max", None)
        if isinstance(hp, int) and isinstance(hp_max, int) and hp > hp_max:
            publish_event(
                "validation_warning",
                {
                    "check": "patch_legality",
                    "turn_id": record.turn_id,
                    "subject": owner,
                    "subject_kind": label,
                    "hp": hp,
                    "hp_max": hp_max,
                    "rationale": "HP exceeds maximum",
                },
                component="validator",
                severity="error",
            )

    for owner, ch in characters.items():
        _check_hp("character", str(owner), ch)
    if isinstance(npc_registry, dict):
        for owner, npc in npc_registry.items():
            _check_hp("npc", str(owner), npc)

    # Dead-actor check: if a patch_type=combat patch references an NPC
    # that the snapshot now reports as dead (hp <= 0), surface a warning.
    dead_npcs = {
        name
        for name, npc in (npc_registry.items() if isinstance(npc_registry, dict) else ())
        if isinstance(getattr(npc, "hp", None), int)
        and getattr(npc, "hp", 0) <= 0
    }
    for patch in record.patches_applied:
        if patch.patch_type != "combat":
            continue
        for field in patch.fields_changed:
            for dead in dead_npcs:
                if dead in field and "hp" not in field:
                    publish_event(
                        "validation_warning",
                        {
                            "check": "patch_legality",
                            "turn_id": record.turn_id,
                            "actor": dead,
                            "rationale": "dead NPC referenced as actor in combat patch",
                        },
                        component="validator",
                        severity="error",
                    )
                    return
```

Register in `Validator.__init__`:

```python
        self.register_check(patch_legality_check)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/validator.py tests/telemetry/test_validator_pipeline.py
git commit -m "feat(validator): patch_legality_check flags HP overflow and dead-actor patches"
```

---

### Task 15: Implement `trope_alignment_check`

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/validator.py`
- Modify: `sidequest-server/tests/telemetry/test_validator_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
from sidequest.telemetry.validator import (
    trope_alignment_check,
    TROPE_KEYWORDS_SOURCE,
)


@pytest.mark.asyncio
async def test_trope_alignment_warns_when_keywords_absent(
    captured_events, monkeypatch,
) -> None:
    """Beat 'desperation' fired but narration lacks any of its keywords."""
    monkeypatch.setitem(
        TROPE_KEYWORDS_SOURCE,
        "desperation",
        ["frantic", "shaking", "ragged", "trembling"],
    )

    record_dict = _make_record().__dict__.copy()
    record_dict["beats_fired"] = [("desperation", 0.7)]
    record_dict["narration"] = "You walk down the hallway calmly."
    record = TurnRecord(**record_dict)

    await trope_alignment_check(record)
    warnings = [e for e in captured_events if e["event_type"] == "validation_warning"]
    assert any(
        "trope_alignment" in str(w["fields"]) for w in warnings
    )


@pytest.mark.asyncio
async def test_trope_alignment_silent_when_keywords_present(
    captured_events, monkeypatch,
) -> None:
    monkeypatch.setitem(
        TROPE_KEYWORDS_SOURCE,
        "desperation",
        ["frantic", "shaking", "ragged"],
    )

    record_dict = _make_record().__dict__.copy()
    record_dict["beats_fired"] = [("desperation", 0.7)]
    record_dict["narration"] = "Your hands are shaking as you reach for the door."
    record = TurnRecord(**record_dict)

    await trope_alignment_check(record)
    warnings = [e for e in captured_events if e["event_type"] == "validation_warning"]
    assert not any("trope_alignment" in str(w["fields"]) for w in warnings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py::test_trope_alignment_warns_when_keywords_absent -v`
Expected: FAIL — `trope_alignment_check` not defined.

- [ ] **Step 3: Implement `trope_alignment_check`**

Add to `validator.py`:

```python
# Per-trope keyword sources — populated lazily from the genre packs the
# first time the check fires. Tests can monkeypatch this dict directly.
# Each value is the list of keywords that "should" appear in narration
# when that trope's beat fires. ADR-031 §"Trope alignment" specifies that
# this is read off each trope's `keywords` list — no second LLM call.
TROPE_KEYWORDS_SOURCE: dict[str, list[str]] = {}


def _trope_keywords(trope: str) -> list[str]:
    if trope in TROPE_KEYWORDS_SOURCE:
        return TROPE_KEYWORDS_SOURCE[trope]
    # Lazy load — the trope catalog is in sidequest.game.trope; importing
    # here at module level would create a cycle. Import on first use,
    # cache the result, and tolerate the absence if the genre layer
    # isn't loaded (e.g. unit tests).
    try:
        from sidequest.game import trope as trope_mod  # noqa: PLC0415

        keywords = getattr(trope_mod, "keywords_for", lambda _t: [])(trope)
        TROPE_KEYWORDS_SOURCE[trope] = list(keywords)
        return TROPE_KEYWORDS_SOURCE[trope]
    except Exception:  # noqa: BLE001
        return []


async def trope_alignment_check(record: TurnRecord) -> None:
    """For each beat that fired this turn, warn if none of the trope's
    keywords appear in narration."""
    if not record.beats_fired:
        return
    narration_lower = (record.narration or "").lower()
    for trope, _threshold in record.beats_fired:
        keywords = _trope_keywords(trope)
        if not keywords:
            continue
        if not any(kw.lower() in narration_lower for kw in keywords):
            publish_event(
                "validation_warning",
                {
                    "check": "trope_alignment",
                    "turn_id": record.turn_id,
                    "trope": trope,
                    "expected_any_of": keywords,
                    "rationale": "trope beat fired but no keywords in narration",
                },
                component="validator",
                severity="warning",
            )
```

Register in `Validator.__init__`:

```python
        self.register_check(trope_alignment_check)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/validator.py tests/telemetry/test_validator_pipeline.py
git commit -m "feat(validator): trope_alignment_check warns on beats fired without keywords"
```

---

### Task 16: Implement `subsystem_exercise_check` and `coverage_gap`

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/validator.py`
- Modify: `sidequest-server/tests/telemetry/test_validator_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
from sidequest.telemetry.validator import subsystem_exercise_check


@pytest.mark.asyncio
async def test_subsystem_exercise_emits_per_turn_summary(captured_events) -> None:
    """Every turn produces a subsystem_exercise_summary event."""
    record = _make_record()
    await subsystem_exercise_check(record)
    summaries = [
        e for e in captured_events
        if e["event_type"] == "subsystem_exercise_summary"
    ]
    assert summaries, "subsystem_exercise_check should emit a per-turn summary"


@pytest.mark.asyncio
async def test_subsystem_exercise_emits_coverage_gap_after_silence(
    captured_events,
) -> None:
    """When a subsystem hasn't fired in N turns, emit coverage_gap."""
    # Reset the sliding window; simulate 11 narrator-only turns.
    from sidequest.telemetry.validator import _reset_subsystem_window

    _reset_subsystem_window()
    for i in range(11):
        record_dict = _make_record(turn_id=i).__dict__.copy()
        record_dict["agent_name"] = "narrator"
        await subsystem_exercise_check(TurnRecord(**record_dict))

    gaps = [e for e in captured_events if e["event_type"] == "coverage_gap"]
    assert gaps, "Expected a coverage_gap after a long subsystem silence"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py::test_subsystem_exercise_emits_per_turn_summary -v`
Expected: FAIL.

- [ ] **Step 3: Implement the check**

Add to `validator.py`:

```python
# Sliding window of (turn_id, agent_name) tuples.
_SUBSYSTEM_WINDOW: deque[tuple[int, str]] = deque(maxlen=50)
_KNOWN_SUBSYSTEMS = {
    "narrator", "combat", "merchant", "world_builder",
    "scenario", "encounter", "chargen", "trope", "barrier",
}
_COVERAGE_GAP_THRESHOLD_TURNS = 10


def _reset_subsystem_window() -> None:
    """Test helper — clears the sliding window."""
    _SUBSYSTEM_WINDOW.clear()


async def subsystem_exercise_check(record: TurnRecord) -> None:
    """Per-turn rollup of which subsystem ran, plus periodic coverage_gap
    when a subsystem hasn't been exercised in N turns."""
    _SUBSYSTEM_WINDOW.append((record.turn_id, record.agent_name))

    publish_event(
        "subsystem_exercise_summary",
        {
            "turn_id": record.turn_id,
            "agent_name": record.agent_name,
            "window_depth": len(_SUBSYSTEM_WINDOW),
        },
        component="validator",
        severity="info",
    )

    if len(_SUBSYSTEM_WINDOW) < _COVERAGE_GAP_THRESHOLD_TURNS:
        return

    recent_agents = {
        agent for _t, agent in list(_SUBSYSTEM_WINDOW)[-_COVERAGE_GAP_THRESHOLD_TURNS:]
    }
    silent = _KNOWN_SUBSYSTEMS - recent_agents
    for sub in silent:
        publish_event(
            "coverage_gap",
            {
                "turn_id": record.turn_id,
                "subsystem": sub,
                "silent_turns": _COVERAGE_GAP_THRESHOLD_TURNS,
                "rationale": "no agent invocation in sliding window",
            },
            component="validator",
            severity="info",
        )
```

Register in `Validator.__init__`:

```python
        self.register_check(subsystem_exercise_check)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/validator.py tests/telemetry/test_validator_pipeline.py
git commit -m "feat(validator): subsystem exercise summary + coverage_gap from sliding window"
```

---

### Task 17: Validator emits `turn_complete` from each TurnRecord

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/validator.py`
- Modify: `sidequest-server/tests/telemetry/test_validator_pipeline.py`

The translator owns most typed events, but `turn_complete` is owned by the validator because it has the full `TurnRecord` (per spec §6.7).

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_validator_emits_turn_complete_first(captured_events) -> None:
    """turn_complete is emitted before the five checks run, and carries
    fields populated from the TurnRecord."""
    v = Validator()
    await v.start()
    try:
        record = _make_record(turn_id=99)
        await v.submit(record)
        # Allow the consumer to process.
        await asyncio.sleep(0.1)
    finally:
        await v.shutdown()

    completes = [e for e in captured_events if e["event_type"] == "turn_complete"]
    assert completes, "validator must emit turn_complete per TurnRecord"
    assert completes[0]["fields"]["turn_id"] == 99
    assert completes[0]["fields"]["agent_name"] == "narrator"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py::test_validator_emits_turn_complete_first -v`
Expected: FAIL.

- [ ] **Step 3: Emit `turn_complete` at the start of `_validate`**

In `validator.py`, modify `_validate` to publish `turn_complete` before iterating checks:

```python
    async def _validate(self, record: TurnRecord) -> None:
        publish_event(
            "turn_complete",
            {
                "turn_id": record.turn_id,
                "player_id": record.player_id,
                "agent_name": record.agent_name,
                "extraction_tier": record.extraction_tier,
                "token_count_in": record.token_count_in,
                "token_count_out": record.token_count_out,
                "agent_duration_ms": record.agent_duration_ms,
                "is_degraded": record.is_degraded,
                "patches_applied": [p.patch_type for p in record.patches_applied],
                "beats_fired": [t for t, _ in record.beats_fired],
            },
            component="validator",
            severity="info",
        )
        for check in self._checks:
            t0 = time.perf_counter()
            try:
                await check(record)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "validator.check_failed check=%s", check.__name__
                )
                publish_event(
                    "validation_warning",
                    {
                        "check": check.__name__,
                        "error": str(exc),
                        "turn_id": record.turn_id,
                    },
                    component="validator",
                    severity="error",
                )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self._check_durations_ms.append(
                (check.__name__, elapsed_ms)
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/validator.py tests/telemetry/test_validator_pipeline.py
git commit -m "feat(validator): emit turn_complete from each TurnRecord"
```

---

### Task 18: Validator health emissions

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/validator.py`
- Modify: `sidequest-server/tests/telemetry/test_validator_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_validator_emits_periodic_queue_depth(captured_events) -> None:
    """Validator surfaces queue_depth as state_transition events."""
    v = Validator()
    v._heartbeat_interval = 0.1  # speed up for the test
    await v.start()
    try:
        await v.submit(_make_record())
        await asyncio.sleep(0.3)  # let heartbeat fire
    finally:
        await v.shutdown()

    health = [
        e for e in captured_events
        if e["event_type"] == "state_transition"
        and e["component"] == "validator"
        and "queue_depth" in str(e["fields"])
    ]
    assert health, "expected validator queue_depth heartbeat"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py::test_validator_emits_periodic_queue_depth -v`
Expected: FAIL.

- [ ] **Step 3: Add the heartbeat task**

In `validator.py`, add to `Validator.__init__`:

```python
        self._heartbeat_interval: float = 30.0
        self._heartbeat_task: asyncio.Task[None] | None = None
```

Modify `start` and `shutdown`:

```python
    async def start(self) -> None:
        if self.is_running():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(
            self._run(), name="sidequest.validator"
        )
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat(), name="sidequest.validator.heartbeat"
        )
        logger.info("validator.started")

    async def shutdown(self, grace_seconds: float = 2.0) -> None:
        self._stopping.set()
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        # ... existing _task shutdown logic ...
        if self._task is None:
            return
        try:
            await asyncio.wait_for(
                self._queue.join(), timeout=grace_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(
                "validator.shutdown_grace_exceeded queued=%d",
                self._queue.qsize(),
            )
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("validator.stopped")
```

Add the `_heartbeat` method:

```python
    async def _heartbeat(self) -> None:
        while not self._stopping.is_set():
            try:
                await asyncio.sleep(self._heartbeat_interval)
            except asyncio.CancelledError:
                return
            durations = list(self._check_durations_ms)
            p50 = _percentile([d for _, d in durations], 50)
            p99 = _percentile([d for _, d in durations], 99)
            publish_event(
                "state_transition",
                {
                    "field": "validator.heartbeat",
                    "queue_depth": self._queue.qsize(),
                    "queue_max": self._queue.maxsize,
                    "dropped_records": self.dropped_records,
                    "check_p50_ms": p50,
                    "check_p99_ms": p99,
                },
                component="validator",
                severity="info",
            )


def _percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(len(s) * pct / 100)))
    return round(s[idx], 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/validator.py tests/telemetry/test_validator_pipeline.py
git commit -m "feat(validator): periodic heartbeat surfaces queue depth and check timing"
```

---

### Task 19: Validator backpressure & crash containment tests

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/test_validator_pipeline.py`

- [ ] **Step 1: Add backpressure and crash-containment tests**

```python
@pytest.mark.asyncio
async def test_validator_survives_crashing_check(captured_events) -> None:
    """A check that raises must not kill the task; other checks still run."""
    v = Validator()

    async def boom(_record: TurnRecord) -> None:
        raise RuntimeError("intentional")

    async def benign(_record: TurnRecord) -> None:
        publish_event(
            "validation_warning",
            {"check": "benign", "noted": True},
            component="validator",
        )

    # Replace registered checks with our two-test set.
    v._checks = [boom, benign]
    await v.start()
    try:
        await v.submit(_make_record())
        await asyncio.sleep(0.2)
    finally:
        await v.shutdown()

    crash_events = [
        e for e in captured_events
        if e["event_type"] == "validation_warning" and "intentional" in str(e["fields"])
    ]
    benign_events = [
        e for e in captured_events
        if e["event_type"] == "validation_warning" and e["fields"].get("check") == "benign"
    ]
    assert crash_events, "crash should be reported as validation_warning"
    assert benign_events, "benign check must still run after the crashing one"


@pytest.mark.asyncio
async def test_backpressure_drops_oldest_and_emits_warning(captured_events) -> None:
    v = Validator(queue_maxsize=2)
    # No consumer running: every submit beyond capacity drops oldest.
    for i in range(5):
        await v.submit(_make_record(turn_id=i))

    drops = [
        e for e in captured_events
        if e["event_type"] == "validation_warning"
        and e["fields"].get("reason") == "queue_full"
    ]
    assert drops, "queue-full should publish a warning"
    assert v.dropped_records >= 3
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_validator_pipeline.py -v`
Expected: PASS — Tasks 11–18 already produced the behavior these tests assert.

- [ ] **Step 3: No-op (tests only)**

If a test reveals a gap (e.g. backpressure warning doesn't fire), patch `Validator.submit` to ensure the warning emits. The intended behavior is already in Task 11's implementation; if a test fails here, fix the regression in `validator.py`.

- [ ] **Step 4: Run the full validator suite**

Run: `cd sidequest-server && uv run pytest tests/telemetry/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add tests/telemetry/test_validator_pipeline.py
git commit -m "test(validator): crash-containment and backpressure coverage"
```

---

### Task 20: Wire validator lifecycle into `app.py`

**Files:**
- Modify: `sidequest-server/sidequest/server/app.py`

- [ ] **Step 1: Write the failing test**

Add to `sidequest-server/tests/server/test_app.py` (extend the existing file):

```python
@pytest.mark.asyncio
async def test_validator_starts_with_app() -> None:
    """create_app() registers a startup hook that boots the validator."""
    from fastapi.testclient import TestClient

    from sidequest.server.app import create_app

    app = create_app()
    with TestClient(app):
        validator = getattr(app.state, "validator", None)
        assert validator is not None, (
            "app.state.validator should be populated at startup"
        )
        assert validator.is_running()
    # On exit, the TestClient's shutdown lifespan triggers shutdown.
    assert not validator.is_running()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_app.py::test_validator_starts_with_app -v`
Expected: FAIL — `app.state.validator` does not exist.

- [ ] **Step 3: Wire the validator in `create_app`**

In `sidequest-server/sidequest/server/app.py`, add to the imports:

```python
from sidequest.telemetry.validator import Validator
```

Inside `create_app`, after the `app.state.watcher_hub = watcher_hub` line, add:

```python
    app.state.validator = Validator()
```

Add a startup handler (alongside `_wire_watcher`):

```python
    @app.on_event("startup")
    async def _start_validator() -> None:
        await app.state.validator.start()
        logger.info("validator.startup_wired")

    @app.on_event("shutdown")
    async def _stop_validator() -> None:
        v = getattr(app.state, "validator", None)
        if v is not None:
            await v.shutdown(grace_seconds=2.0)
            logger.info("validator.shutdown_wired")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_app.py -v`
Expected: PASS.

Run: `cd sidequest-server && uv run pytest tests/server/ tests/telemetry/ -v -x`
Expected: PASS — full server + telemetry suite green.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/server/app.py tests/server/test_app.py
git commit -m "feat(server): wire Validator lifecycle into FastAPI startup/shutdown"
```

---

### Task 21: Assemble TurnRecord at dispatch and submit to validator

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py`

- [ ] **Step 1: Identify TurnRecord-source data in dispatch**

Run: `cd sidequest-server && grep -n "turn_id\|narration\|patches\|beats_fired\|extraction_tier\|token_count\|duration_ms\|is_degraded" sidequest/server/session_handler.py | head -40`
Expected: locations in dispatch where each field's source value already exists. Some fields (e.g. `extraction_tier`, `token_count_in`, `is_degraded`) may already be tracked by the agent client; others may need to be threaded back from `orchestrator.process_action`.

If a field has no obvious source: default to a sentinel (`extraction_tier=1`, `token_count_in=0`, `is_degraded=False`) — this plan does not block on perfect field population. Follow-up plans for the agent emission family will tighten these.

- [ ] **Step 2: Write the wiring test**

Add to `sidequest-server/tests/server/test_turn_span_wiring.py`:

```python
@pytest.mark.asyncio
async def test_dispatch_submits_turn_record_to_validator(server_fixture) -> None:
    """At dispatch end, a TurnRecord lands on app.state.validator's queue."""
    submitted: list = []

    async def fake_submit(record):
        submitted.append(record)

    # Patch the validator's submit so we observe what the dispatch sends.
    with patch.object(
        server_fixture.app.state.validator, "submit", new=fake_submit
    ):
        await server_fixture.dispatch_action(
            player="alice",
            text="I look around.",
        )

    assert submitted, "dispatch must submit a TurnRecord at end of turn"
    record = submitted[0]
    assert record.player_id == "alice"
    assert record.player_input == "I look around."
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_turn_span_wiring.py::test_dispatch_submits_turn_record_to_validator -v`
Expected: FAIL — no TurnRecord assembly in dispatch yet.

- [ ] **Step 4: Add TurnRecord assembly inside `turn_span()`**

In `session_handler.py`, modify the dispatch coroutine wrapped by `turn_span()` (Task 9). Inside the `with turn_span(...)` block, at the end (after narration/patches are computed), assemble and submit:

```python
from datetime import UTC, datetime
from hashlib import blake2b

from sidequest.telemetry.turn_record import PatchSummary, TurnRecord


def _hash_snapshot(snap: object) -> str:
    """Cheap stable hash of a snapshot for replay-keying / change-detection.

    blake2b over the snapshot's repr — repr is not formally stable, but
    snapshots are dataclasses/pydantic models with deterministic field
    order so it's stable in practice. If a future test asserts identity
    across processes, swap to a JSON-serialized canonical form.
    """
    return blake2b(repr(snap).encode(), digest_size=16).hexdigest()


# ... inside the dispatch coroutine, after patches and narration are computed:
record = TurnRecord(
    turn_id=turn_id,
    timestamp=datetime.now(UTC),
    player_id=player_id,
    player_input=text,
    classified_intent=classified_intent,
    agent_name=agent_name,
    narration=narration_text,
    patches_applied=[
        PatchSummary(
            patch_type=p.kind if hasattr(p, "kind") else "world",
            fields_changed=list(p.fields_changed) if hasattr(p, "fields_changed") else [],
        )
        for p in patches_applied
    ],
    snapshot_before_hash=_hash_snapshot(snapshot_before),
    snapshot_after=snapshot_after,
    delta=delta,
    beats_fired=list(beats_fired) if beats_fired else [],
    extraction_tier=getattr(agent_result, "extraction_tier", 1),
    token_count_in=getattr(agent_result, "token_count_in", 0),
    token_count_out=getattr(agent_result, "token_count_out", 0),
    agent_duration_ms=int(getattr(agent_result, "duration_ms", 0)),
    is_degraded=getattr(agent_result, "is_degraded", False),
)

validator = self._room_registry.app_state.validator if hasattr(self, "_room_registry") else None
# Plumb app.state.validator to the session handler — see Step 5.
if validator is None:
    validator = getattr(self, "_validator", None)
if validator is not None:
    await validator.submit(record)
```

The variable names (`patches_applied`, `narration_text`, `agent_result`, etc.) come from whatever the existing dispatch already binds; align with the actual identifiers in `session_handler.py`.

- [ ] **Step 5: Plumb the validator reference**

The session handler needs access to `app.state.validator`. Two options:

1. **Constructor injection.** If `WebSocketSessionHandler.__init__` already takes app state, add `validator: Validator` to it; thread through from `app.py` where the handler is constructed.
2. **Late import.** If construction is hidden behind a factory, import lazily: `from sidequest.server.app import _resolve_validator` (a module-level helper that reaches into the active app instance).

Prefer option 1 (constructor injection) — explicit, testable, and follows the existing DI pattern (`claude_client_factory`, `genre_pack_search_paths`, etc.). Modify `app.py` where `WebSocketSessionHandler` is constructed to pass `validator=app.state.validator`.

Concretely in `app.py`, locate the `WebSocketSessionHandler(...)` call (likely in the `/ws` endpoint) and add the `validator=app.state.validator` kwarg. Then add the parameter to `WebSocketSessionHandler.__init__` and store it as `self._validator`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_turn_span_wiring.py -v`
Expected: PASS.

Run: `cd sidequest-server && uv run pytest tests/server/ tests/telemetry/ -v -x`
Expected: PASS — full suite green.

- [ ] **Step 7: Commit**

```bash
cd sidequest-server
git add sidequest/server/session_handler.py sidequest/server/app.py tests/server/test_turn_span_wiring.py
git commit -m "feat(server): assemble TurnRecord at dispatch end and submit to validator"
```

---

## Phase 4 — Sweep & Cleanup

### Task 22: Update the `watcher.ts` source comment

**Files:**
- Modify: `sidequest-ui/src/types/watcher.ts`

- [ ] **Step 1: Inspect the current comment**

Run: `head -20 sidequest-ui/src/types/watcher.ts`
Expected: a header comment mentioning `sidequest-server/src/lib.rs` (Rust-era reference).

- [ ] **Step 2: Replace the source pointer**

Replace the Rust-pointing comment with:

```typescript
// Mirrors the Python WatcherEvent contract emitted by:
//   - sidequest-server/sidequest/telemetry/spans.py (SPAN_ROUTES)
//   - sidequest-server/sidequest/server/watcher.py  (WatcherSpanProcessor)
//   - sidequest-server/sidequest/telemetry/validator.py (Layer-3 events)
// See ADR-031 (Game Watcher) and ADR-089 (Dashboard Restoration).
```

- [ ] **Step 3: No-op (docs only)**

Run: `cd sidequest-ui && npx tsc --noEmit` (or `just client-lint`)
Expected: PASS — comment changes don't affect types.

- [ ] **Step 4: No tests needed**

Pure docstring change.

- [ ] **Step 5: Commit**

```bash
cd sidequest-ui
git add src/types/watcher.ts
git commit -m "docs(watcher): point header at Python source modules"
```

---

### Task 23: Author ADR-089

**Files:**
- Create: `docs/adr/089-otel-dashboard-restoration.md`

- [ ] **Step 1: Inspect the ADR frontmatter schema**

Run: `head -30 docs/adr/088-adr-frontmatter-schema-and-auto-generated-indexes.md`
Expected: the canonical frontmatter block. Use it as a template.

Also: `cat docs/adr/README.md | head -60` for the load-bearing-flag and category conventions.

- [ ] **Step 2: Write the ADR**

Create `docs/adr/089-otel-dashboard-restoration.md`:

```markdown
---
id: ADR-089
title: OTEL Dashboard Restoration after Python Port
status: accepted
date: 2026-04-25
authors: [architect]
related: [031, 058, 082]
supersedes: []
implementation-status: live
load-bearing: true
categories: [Telemetry, Project Lifecycle]
---

# ADR-089: OTEL Dashboard Restoration after Python Port

## Status

**Accepted** — 2026-04-25.

## Context

After the Rust → Python port (ADR-082), the OTEL dashboard at `/ws/watcher`
and the React `Dashboard/` panes degraded materially. The CLAUDE.md
"OTEL Observability Principle" was no longer enforced: the GM panel — the
"lie detector" Sebastien-the-mechanics-first-player and Keith-the-builder
both depend on — surfaced almost no live signal.

A forensic audit found four failures:

1. The `just otel` recipe pointed at a deleted `playtest.py`.
2. Most `WatcherEventType` values declared in `watcher.ts` had zero or one
   emission sites in production code.
3. `~80%` of `SPAN_*` constants in `telemetry/spans.py` were transcribed
   from Rust but never re-implanted into Python dispatch — the catalog
   was aspirational.
4. The translator (`WatcherSpanProcessor.on_end`) flattened every span
   to `agent_span_close` with no semantic typed-event routing.

The Python port copied the **vocabulary** and **transport** but not the
**emission discipline** or the **Layer-3 narrative validator**.

## Decision

Restore the dashboard to ADR-031's three-layer semantic-telemetry contract,
faithfully ported to Python, with three deliberate departures from the
Rust ADR:

1. **`TurnRecord` shape.** Store `snapshot_before_hash + snapshot_after +
   StateDelta` rather than two full `GameSnapshot` clones. Same
   validation power, no double-clone cost.
2. **Validator transport.** `asyncio.Queue(maxsize=32)` with oldest-record
   drop on backpressure (faithful to ADR-031's "lossy by design" intent).
3. **Console exporter gating.** `ConsoleSpanExporter` defaults off; gated
   behind `SIDEQUEST_OTEL_CONSOLE=1` for debug.

The translator gains a routing table (`SPAN_ROUTES`) colocated with span
constants in `spans.py` so renaming a constant breaks the route at import
and a new constant without a routing decision trips the
`test_routing_completeness.py` lint.

A new `Validator` task consumes `TurnRecord`s and runs five deterministic
checks: entity, inventory, patch-legality, trope-alignment,
subsystem-exercise. The validator owns `turn_complete`, `coverage_gap`,
and `validation_warning`.

## Consequences

### Positive

- Every `WatcherEventType` declared in `watcher.ts` has a clear owner;
  no orphans, no double-emission.
- Adding a new span constant requires an explicit routing decision —
  catches the regression that caused this work.
- The "lie detector" property is restored: subsystem activity surfaces
  on the dashboard whether or not the LLM mentions it.
- `just otel` is CI-protected against future script renames.

### Negative

- `~80` emission sites still need re-implanting (Phase 2 follow-up plans).
  The infrastructure now in place makes each rollout a small, repeatable
  change rather than a system-wide redesign.
- Validator runs on the same event loop as dispatch. Bounded queue + lossy
  drop policy keeps it from impacting hot-path latency, but heavy check
  overhead would still serialize behind dispatch. Acceptable for current
  playtest scale (≤5 watchers, ≤1 turn/sec).

### Out of scope

- No `TurnRecord` persistence / replay — ADR-031 mentions it as a future
  possibility; not building now.
- No second-LLM validation. ADR-031's "God lifting rocks" prohibition
  stands.
- No Pennyfarthing-style HTTP OTLP receiver. In-process span processor
  remains.

## Implementation

See `docs/superpowers/specs/2026-04-25-otel-dashboard-restoration-design.md`
for the design and `docs/superpowers/plans/2026-04-25-otel-dashboard-restoration.md`
for the task plan.

## Related

- ADR-031: Game Watcher — Semantic Telemetry (this ADR ports it to Python)
- ADR-058: Claude subprocess OTEL passthrough (unchanged)
- ADR-082: Port `sidequest-api` from Rust back to Python (this ADR closes one of its drift items)
```

- [ ] **Step 3: Validate the ADR file**

Run: `python3 scripts/regenerate_adr_indexes.py --check 2>&1 || python3 scripts/regenerate_adr_indexes.py`
Expected: regenerates indexes and includes ADR-089. If `--check` is unsupported, just regenerate.

- [ ] **Step 4: Inspect the regenerated index**

Run: `grep -n "089" docs/adr/README.md CLAUDE.md 2>&1 | head`
Expected: ADR-089 appears in both.

- [ ] **Step 5: Commit**

```bash
git add docs/adr/089-otel-dashboard-restoration.md docs/adr/README.md CLAUDE.md
git commit -m "docs(adr): ADR-089 OTEL Dashboard Restoration after Python Port"
```

---

### Task 24: Amend ADR-031 with the Python-port section

**Files:**
- Modify: `docs/adr/031-game-watcher-semantic-telemetry.md`

- [ ] **Step 1: Inspect the current ADR-031**

Run: `grep -n "## " docs/adr/031-game-watcher-semantic-telemetry.md`
Expected: list of section headers. Identify where to insert a "Python-port" subsection.

- [ ] **Step 2: Append the port section and update status**

At the end of `docs/adr/031-game-watcher-semantic-telemetry.md`, before the trailing line if any, append:

```markdown
---

## Python-port note (2026-04-25)

After ADR-082 ported the backend from Rust to Python, the canonical
implementation lives in:

- `sidequest-server/sidequest/telemetry/spans.py` — span name catalog,
  `SpanRoute` mechanism, `SPAN_ROUTES`, `FLAT_ONLY_SPANS`, helper
  context managers.
- `sidequest-server/sidequest/server/watcher.py` — `WatcherSpanProcessor`
  translator (Layer 1 + typed-event routing).
- `sidequest-server/sidequest/telemetry/validator.py` — Layer-3 narrative
  validator (`Validator` class, five checks).
- `sidequest-server/sidequest/telemetry/turn_record.py` — `TurnRecord`
  dataclass.

Code references in this ADR pre-2026-04-19 point at the Rust tree archived
at https://github.com/slabgorb/sidequest-api. The Rust phasing table is
preserved as historical context but the active phase descriptions are
superseded by ADR-089.

`implementation-status: live` is re-affirmed for the Python port as of
ADR-089's completion.
```

If the existing ADR-031 frontmatter has `implementation-status: drift` or `partial`, flip it back to `live`:

```yaml
implementation-status: live
```

- [ ] **Step 3: Regenerate the ADR index again**

Run: `python3 scripts/regenerate_adr_indexes.py`
Expected: re-emits indexes; ADR-031 should no longer carry the drift marker.

- [ ] **Step 4: Verify CLAUDE.md ADR Index**

Run: `grep -A2 "031.*Game Watcher" CLAUDE.md`
Expected: line no longer ends in `*(drift)*`.

- [ ] **Step 5: Commit**

```bash
git add docs/adr/031-game-watcher-semantic-telemetry.md docs/adr/README.md CLAUDE.md docs/adr/DRIFT.md
git commit -m "docs(adr): amend ADR-031 with Python-port section, flip status to live"
```

---

### Task 25: Final aggregate gate

**Files:**
- (no source changes — final verification step)

- [ ] **Step 1: Run the full check-all gate**

Run: `just check-all`
Expected: PASS — server lint, server tests, client lint, client tests, daemon lint all green.

- [ ] **Step 2: Run the routing-completeness lint explicitly**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_routing_completeness.py -v`
Expected: PASS.

- [ ] **Step 3: Boot the dashboard end-to-end**

Run: `just up` in one terminal, then in another: `just otel` and confirm the browser-friendly viewer at `http://localhost:9765` loads without errors. Drive a single turn through the running game and confirm the dashboard shows:

- `agent_span_open` (handshake)
- `agent_span_close` flow (Timeline tab)
- `turn_complete` (validator emission)
- `state_transition` events for currently-routed spans
- `subsystem_exercise_summary` per turn

If any expected event is missing, work back through Tasks 5–21 to identify the broken link.

- [ ] **Step 4: Tear down cleanly**

Run: `just down`
Expected: services stop without errors; no orphaned validator tasks per the shutdown logs.

- [ ] **Step 5: Final commit (if any sweep changes were needed)**

If Step 3 surfaced any small routing gaps, fix them and commit:

```bash
cd sidequest-server
git add -p  # stage only the routing fix
git commit -m "fix(telemetry): close routing gap surfaced by end-to-end smoke"
```

If no fixes needed, skip this step.

---

## Self-Review

**1. Spec coverage:**

| Spec section | Tasks |
|---|---|
| §1.1 broken `just otel` | Task 1 |
| §1.2 dashboard contract stubs | Tasks 5, 6, 8, 11–17 |
| §1.3 ~80% dead spans (turn root) | Tasks 8, 9 |
| §1.4 impoverished translator | Tasks 4, 5, 6 |
| §2.1 dep-1: TurnRecord shape | Task 10 |
| §2.1 dep-2: validator queue | Task 11 |
| §2.1 dep-3: console exporter gating | Task 2 |
| §3 architecture diagram | Tasks 4–21 (all three layers) |
| §4 family table — turn_root | Tasks 8, 9 |
| §4 family table — non-turn families | **Out of scope — follow-up plans** |
| §4.2 implementation conventions | Tasks 5, 8 (helper-first; required attrs) |
| §5.1 TurnRecord dataclass | Task 10 |
| §5.2 pipeline | Tasks 11, 20, 21 |
| §5.3 five checks | Tasks 12–17 |
| §5.4 health & self-observation | Task 18 |
| §6.1–6.4 translator routing | Tasks 4, 5, 6 |
| §6.5 severity inference | Task 6 |
| §6.6 publish_event migration | **Deferred to follow-up plans (per-family)** |
| §6.7 ownership matrix | Tasks 4–21 (each event type owned somewhere) |
| §7.1 three test layers | Tasks 8, 9, 11–21 |
| §7.2 routing completeness lint | Task 7 |
| §7.3 validator pipeline tests | Tasks 11, 19 |
| §7.4 P0 smoke test | Task 3 |
| §8 sequencing | Phase 0/1/3/4 in scope; Phase 2 family rollouts deferred |
| §9 deliverables | Tasks 1, 2, 7, 10, 11, 20, 22, 23, 24 |
| §10 ADR linkage | Tasks 23, 24 |

Phase 2's ~24 non-turn emission families are the only deliberate gap, called out explicitly in the plan header.

**2. Placeholder scan:** No "TBD"/"TODO"/"fill in"/"similar to Task N" — every code step has actual code. Every command step has the literal command. Field names in `TurnRecord` (Task 10) are reused unchanged in Tasks 11–21.

**3. Type consistency:** `Validator.submit`/`is_running`/`shutdown` referenced consistently. `TurnRecord` field names match across producers (Task 21) and consumers (Tasks 12–17). `SpanRoute` `event_type`/`component`/`extract` fields stable across Tasks 4–6.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-25-otel-dashboard-restoration.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for a 25-task plan because reviewer eyes every commit and the main session stays uncluttered.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

Which approach, Dear Viewer?
