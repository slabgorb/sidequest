# Python Port — Phase 0 (Scaffold) + Phase 1 (Narration Vertical Slice) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port `sidequest-api` (Rust) to `sidequest-server` (Python) through Phase 1 of ADR-082's execution strategy — the thinnest vertical slice that delivers playable parity for narration. Result: a Python FastAPI server that accepts WebSocket connections, processes `PLAYER_ACTION` messages through the narrator agent (Claude subprocess), returns `NARRATION`, and persists session state.

**Architecture:** Eight stories (41-0 through 41-7) across two phases. Phase 0 scaffolds `sidequest-server` from empty to "FastAPI skeleton starts, pytest runs clean, OTEL tracer initialises." Phase 1 ports `protocol`, `genre` (with the authorized `LayeredMerge` consolidation), a minimal slice of `game`, `telemetry` span catalog, the narrator agent, and the server dispatch — enough to complete a narration turn end-to-end. 1:1 crate-to-package composition is preserved; the genre consolidation is the only authorized refactor.

**Tech Stack:** Python 3.12+, FastAPI + uvicorn, pydantic v2, pytest + pytest-asyncio, opentelemetry-api + opentelemetry-sdk, Claude CLI subprocess via `asyncio.create_subprocess_exec`, SQLite via stdlib `sqlite3` for save files. No ORM — raw SQL where needed (per the Rust tree's pattern of `rusqlite`).

**Reference:** [ADR-082](../../adr/082-port-api-rust-to-python.md) for rationale, [strategy spec](../specs/2026-04-19-python-port-execution-strategy-design.md) for the 8-phase breakdown and anchoring decisions.

---

## Rust → Python Translation Key

Port stories (41-1 through 41-6) apply these rules when translating Rust source to Python. Mechanical translations are not re-documented per task; only non-mechanical decisions are called out.

| Rust | Python |
|---|---|
| `struct Foo { ... }` with `#[derive(Serialize, Deserialize)]` | `class Foo(BaseModel)` with pydantic v2 |
| `enum Variant` with serde tag/content | `Annotated[Union[V1, V2, ...], Field(discriminator='type')]` |
| `Option<T>` | `T \| None` |
| `Vec<T>` | `list[T]` |
| `HashMap<K, V>` | `dict[K, V]` |
| `Result<T, E>` | Raise exception (domain-specific subclass of `Exception`) |
| `&str` / `String` / `Cow<str>` | `str` |
| `i32` / `u32` / `usize` / `u64` | `int` |
| `f32` / `f64` | `float` |
| `bool` | `bool` |
| `tokio::process::Command` | `asyncio.create_subprocess_exec` |
| `#[tokio::test] async fn foo()` | `@pytest.mark.asyncio\nasync def test_foo()` |
| `#[test] fn foo()` | `def test_foo()` |
| `assert_eq!(a, b)` | `assert a == b` |
| `assert!(expr)` | `assert expr` |
| `#[should_panic(expected = "...")]` | `with pytest.raises(ExceptionType, match="..."):` |
| `tracing::info_span!("name", attr = value)` | `tracer.start_as_current_span("name", attributes={"attr": value})` |
| `serde_json::to_string(&x)?` | `x.model_dump_json()` |
| `serde_json::from_str::<T>(s)?` | `T.model_validate_json(s)` |
| `Arc<Mutex<T>>` | `asyncio.Lock()` + plain reference (single-process, cooperative concurrency) |
| `tokio::sync::mpsc::channel` | `asyncio.Queue` |

**Preserved verbatim:** struct/field/method names (snake_case → snake_case; PascalCase → PascalCase), test function names, OTEL span names, error variant names. Renaming during the port is a deviation and must be logged.

---

## File Structure

The port target is `/Users/keithavery/Projects/oq-1/sidequest-server/`. Phase 0 creates the skeleton; Phase 1 fills the Phase-1-relevant pieces of each package.

```
sidequest-server/
├── pyproject.toml                          # Phase 0 — project manifest, deps, tool configs
├── README.md                               # (exists) — no changes
├── .gitignore                              # (exists) — no changes
├── sidequest/
│   ├── __init__.py                         # Phase 0 — version, top-level exports
│   ├── protocol/                           # Story 41-1
│   │   ├── __init__.py
│   │   ├── messages.py                     # GameMessage, discriminated union of all MessageType payloads
│   │   └── types.py                        # Shared enum/type aliases (MessageType, PlayerId, SessionId)
│   ├── genre/                              # Story 41-2
│   │   ├── __init__.py
│   │   ├── resolver.py                     # LayeredMerge base class (the consolidation)
│   │   ├── loader.py                       # YAML → pydantic loader, base→genre→world merge driver
│   │   ├── models/                         # ported from sidequest-genre/src/models/
│   │   │   ├── __init__.py
│   │   │   ├── archetype.py
│   │   │   ├── axis.py
│   │   │   ├── lore.py
│   │   │   └── <others per Rust tree>
│   │   ├── cache.py                        # resolved-pack cache
│   │   └── error.py                        # genre-loader exceptions
│   ├── game/                               # Story 41-3 (Phase 1: minimal slice only)
│   │   ├── __init__.py
│   │   ├── character.py                    # Character model (Phase 1 subset)
│   │   ├── session.py                      # Session, GameState (Phase 1 subset)
│   │   └── commands.py                     # minimal command enum for narrator dispatch
│   ├── telemetry/                          # Story 41-4
│   │   ├── __init__.py
│   │   ├── spans.py                        # span name constants + helpers
│   │   └── setup.py                        # tracer provider initialization
│   ├── agents/                             # Story 41-5 (Phase 1: narrator only)
│   │   ├── __init__.py
│   │   ├── claude_agent.py                 # Claude subprocess runner (ported from sidequest-agents/src/claude_agent.rs)
│   │   ├── narrator.py                     # Narrator agent (Phase 1 turn pipeline)
│   │   └── prompt_builder.py               # Minimal prompt assembly for narration
│   ├── daemon_client/                      # empty placeholder — daemon out of scope (ADR-082)
│   │   └── __init__.py
│   ├── server/                             # Story 41-6
│   │   ├── __init__.py
│   │   ├── app.py                          # FastAPI application
│   │   ├── websocket.py                    # WebSocket handler, dispatch loop
│   │   ├── session_handler.py              # per-connection state, save/load
│   │   └── dispatch.py                     # message → agent routing (Phase 1: PLAYER_ACTION → narrator only)
│   └── cli/                                # Phase 7 — empty placeholders in Phase 0
│       ├── __init__.py
│       ├── promptpreview/__init__.py
│       ├── encountergen/__init__.py
│       ├── loadoutgen/__init__.py
│       ├── namegen/__init__.py
│       └── validate/__init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py                         # shared fixtures (event loop, tmp_path, content_dir)
│   ├── smoke/                              # Phase 0 smoke
│   │   └── test_skeleton_starts.py
│   ├── protocol/                           # Story 41-1
│   │   ├── __init__.py
│   │   ├── test_messages.py
│   │   └── fixtures/                       # captured Rust-oracle wire outputs
│   ├── genre/                              # Story 41-2
│   │   ├── __init__.py
│   │   ├── test_layered_merge.py
│   │   ├── test_loader.py
│   │   └── test_models/
│   ├── game/                               # Story 41-3
│   │   ├── __init__.py
│   │   ├── test_character.py
│   │   └── test_session.py
│   ├── telemetry/                          # Story 41-4
│   │   ├── __init__.py
│   │   └── test_spans.py
│   ├── agents/                             # Story 41-5
│   │   ├── __init__.py
│   │   ├── test_claude_agent.py
│   │   └── test_narrator.py
│   └── server/                             # Story 41-6
│       ├── __init__.py
│       ├── test_websocket.py
│       └── test_dispatch.py
├── scripts/
│   └── capture_wire_fixture.py             # Phase 1 — Rust-oracle wire capture harness
└── justfile                                # orchestrator-side; updated during cut-over
```

---

## Phase 0 — Story 41-0: Scaffold `sidequest-server`

**Goal:** From empty repo to "FastAPI skeleton starts, `pytest` runs clean, OTEL tracer initialises, 15 empty packages laid out, one smoke test passes."

**Workflow:** trivial (no behavioral tests yet, purely infrastructure).

**Repo:** `sidequest-server` (the inline subrepo at `oq-1/sidequest-server/`).

**Branch:** `feat/41-0-scaffold` off `develop`.

### Task 1: Create `pyproject.toml`

**Files:**
- Create: `sidequest-server/pyproject.toml`

- [ ] **Step 1: Write `pyproject.toml` with minimum deps**

```toml
[project]
name = "sidequest-server"
version = "0.1.0"
description = "SideQuest Python API server — port target of sidequest-api (Rust). See ADR-082."
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "pydantic>=2.6",
    "pyyaml>=6.0",
    "opentelemetry-api>=1.24",
    "opentelemetry-sdk>=1.24",
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.3",
    "pyright>=1.1.358",
]

[project.scripts]
sidequest-server = "sidequest.server.app:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]  # line-length handled by formatter
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore(41-0): add pyproject.toml with FastAPI/pydantic/pytest deps"
```

### Task 2: Create the 15-package skeleton

**Files:**
- Create: `sidequest-server/sidequest/__init__.py`
- Create: 15 package `__init__.py` files per the File Structure map above

- [ ] **Step 1: Write top-level `__init__.py`**

```python
"""SideQuest server — Python port of sidequest-api (Rust).

See ADR-082 for rationale and the port strategy spec for the phase breakdown.
"""

__version__ = "0.1.0"
```

- [ ] **Step 2: Create all empty package `__init__.py` files**

```bash
mkdir -p sidequest/protocol sidequest/genre/models sidequest/game
mkdir -p sidequest/telemetry sidequest/agents sidequest/daemon_client
mkdir -p sidequest/server sidequest/cli
mkdir -p sidequest/cli/promptpreview sidequest/cli/encountergen
mkdir -p sidequest/cli/loadoutgen sidequest/cli/namegen sidequest/cli/validate

# Create __init__.py files
touch sidequest/protocol/__init__.py
touch sidequest/genre/__init__.py
touch sidequest/genre/models/__init__.py
touch sidequest/game/__init__.py
touch sidequest/telemetry/__init__.py
touch sidequest/agents/__init__.py
touch sidequest/daemon_client/__init__.py
touch sidequest/server/__init__.py
touch sidequest/cli/__init__.py
touch sidequest/cli/promptpreview/__init__.py
touch sidequest/cli/encountergen/__init__.py
touch sidequest/cli/loadoutgen/__init__.py
touch sidequest/cli/namegen/__init__.py
touch sidequest/cli/validate/__init__.py
```

Each `__init__.py` under `daemon_client/`, and the CLI placeholders, contain one comment:

```python
# Placeholder — populated in later phases per ADR-082 port plan.
```

- [ ] **Step 3: Commit**

```bash
git add sidequest/
git commit -m "chore(41-0): scaffold 15-package Python skeleton (1:1 Rust crate mapping)"
```

### Task 3: Create the FastAPI skeleton

**Files:**
- Create: `sidequest-server/sidequest/server/app.py`

- [ ] **Step 1: Write the minimal FastAPI app**

```python
"""FastAPI application entry point for sidequest-server."""

from __future__ import annotations

import asyncio
import logging

import uvicorn
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Construct the FastAPI application.

    Phase 0: empty skeleton. Phase 1 wires /ws WebSocket endpoint via
    sidequest.server.websocket.register(app).
    """
    app = FastAPI(
        title="sidequest-server",
        description="SideQuest Python API server (ADR-082 port target)",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def main() -> None:
    """Entry point for `sidequest-server` CLI script."""
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add sidequest/server/app.py
git commit -m "chore(41-0): FastAPI skeleton with /health endpoint"
```

### Task 4: Configure OTEL tracer initialization

**Files:**
- Create: `sidequest-server/sidequest/telemetry/setup.py`
- Create: `sidequest-server/sidequest/telemetry/__init__.py`

- [ ] **Step 1: Write the tracer setup module**

```python
"""OpenTelemetry tracer setup for sidequest-server.

Phase 0: console exporter only. Phase 1+ adds OTLP exporter via env config.
"""

from __future__ import annotations

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
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    _initialized = True


def tracer():
    """Return the sidequest-server tracer."""
    return trace.get_tracer("sidequest-server")
```

- [ ] **Step 2: Write the `__init__.py` exports**

```python
"""OTEL telemetry for sidequest-server."""

from sidequest.telemetry.setup import init_tracer, tracer

__all__ = ["init_tracer", "tracer"]
```

- [ ] **Step 3: Commit**

```bash
git add sidequest/telemetry/
git commit -m "chore(41-0): OTEL tracer setup with ConsoleSpanExporter"
```

### Task 5: Configure pytest with conftest

**Files:**
- Create: `sidequest-server/tests/__init__.py` (empty)
- Create: `sidequest-server/tests/conftest.py`

- [ ] **Step 1: Write the conftest**

```python
"""Shared pytest fixtures for sidequest-server tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def content_dir() -> Path:
    """Path to the sidequest-content repo (genre packs, worlds)."""
    # Repo sibling of sidequest-server
    return Path(__file__).resolve().parent.parent.parent / "sidequest-content"


@pytest.fixture
def tmp_save_dir(tmp_path: Path) -> Path:
    """Temporary save directory per test."""
    save_dir = tmp_path / "saves"
    save_dir.mkdir()
    return save_dir


@pytest.fixture
async def initialized_tracer() -> AsyncIterator[None]:
    """Initialize OTEL tracer for the duration of a test."""
    from sidequest.telemetry import init_tracer

    init_tracer(service_name="sidequest-server-test")
    yield
```

- [ ] **Step 2: Create empty tests init**

```bash
touch tests/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add tests/__init__.py tests/conftest.py
git commit -m "chore(41-0): pytest conftest with content/save/tracer fixtures"
```

### Task 6: Write the smoke test

**Files:**
- Create: `sidequest-server/tests/smoke/__init__.py` (empty)
- Create: `sidequest-server/tests/smoke/test_skeleton_starts.py`

- [ ] **Step 1: Write the smoke test**

```python
"""Smoke tests proving the Phase 0 skeleton is wired correctly."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sidequest.server.app import create_app
from sidequest.telemetry import init_tracer, tracer


def test_fastapi_app_constructs() -> None:
    """The FastAPI app can be built without error."""
    app = create_app()
    assert app.title == "sidequest-server"


def test_health_endpoint_returns_ok() -> None:
    """The /health endpoint responds 200 with {status: ok}."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_otel_tracer_initializes() -> None:
    """The OTEL tracer can be initialized idempotently."""
    init_tracer()
    init_tracer()  # idempotent
    t = tracer()
    with t.start_as_current_span("smoke-span") as span:
        assert span is not None
```

- [ ] **Step 2: Create empty smoke tests init**

```bash
touch tests/smoke/__init__.py
```

- [ ] **Step 3: Run the smoke test**

```bash
cd sidequest-server
pip install -e ".[dev]"
pytest tests/smoke/ -v
```

Expected output:
```
tests/smoke/test_skeleton_starts.py::test_fastapi_app_constructs PASSED
tests/smoke/test_skeleton_starts.py::test_health_endpoint_returns_ok PASSED
tests/smoke/test_skeleton_starts.py::test_otel_tracer_initializes PASSED
```

- [ ] **Step 4: Commit**

```bash
git add tests/smoke/
git commit -m "test(41-0): smoke test proves FastAPI + OTEL skeleton wires up"
```

### Task 7: Add orchestrator `just` recipes

**Files:**
- Modify: `/Users/keithavery/Projects/oq-1/justfile` — add `server-*` recipes

- [ ] **Step 1: Read existing justfile to find the `api-*` section**

```bash
grep -n "^api-" /Users/keithavery/Projects/oq-1/justfile
```

- [ ] **Step 2: Add the `server-*` recipes below the `api-*` block**

```just
# Python server recipes (ADR-082 port target)

server-dev:
    cd sidequest-server && uvicorn sidequest.server.app:create_app --factory --reload --host 127.0.0.1 --port 8080

server-test:
    cd sidequest-server && pytest -v

server-lint:
    cd sidequest-server && ruff check .

server-fmt:
    cd sidequest-server && ruff format .

server-check: server-lint server-test
```

- [ ] **Step 3: Verify recipes work**

```bash
just server-test
```

Expected: smoke tests pass.

- [ ] **Step 4: Commit on the orchestrator repo**

```bash
cd /Users/keithavery/Projects/oq-1
git add justfile
git commit -m "chore(41-0): add server-* just recipes for sidequest-server"
```

**Note:** This commit is on the orchestrator repo on `docs/adr-082-port-strategy` branch. The `sidequest-server` commits from Tasks 1–6 are on `sidequest-server`'s `feat/41-0-scaffold` branch.

### Task 8: Mark Story 41-0 complete

**Files:**
- The `sidequest-server` feature branch `feat/41-0-scaffold` gets a PR to `develop`
- Orchestrator session file updated

- [ ] **Step 1: Push the sidequest-server feature branch**

From a terminal (not Claude Bash — pf hook blocks direct pushes):
```bash
cd /Users/keithavery/Projects/oq-1/sidequest-server
git push -u origin feat/41-0-scaffold
gh pr create --base develop --title "Story 41-0: Scaffold sidequest-server" --body "Phase 0 of ADR-082 port. 15-package Python skeleton, FastAPI + OTEL wired, smoke tests pass."
```

- [ ] **Step 2: Merge the PR, verify develop is green**

```bash
gh pr merge --squash
cd /Users/keithavery/Projects/oq-1/sidequest-server
git checkout develop && git pull
just server-test   # from orchestrator
```

Expected: all smoke tests pass on `develop`.

**DoD for Phase 0:** 
- `just server-test` runs and passes (green).
- `just server-dev` binds port 8080 and `curl localhost:8080/health` returns `{"status": "ok"}`.
- OTEL tracer initializes without error.
- Every `__init__.py` in the 15-package skeleton exists and is importable.

---

## Phase 1 — Narration Vertical Slice

Phase 1 fills in just-enough of each package to complete one end-to-end narration turn. Each story has its own branch and its own PR, numbered 41-1 through 41-7.

### Per-story TDD discipline (applies to all 41-1 through 41-6)

Every port story follows the loop from the strategy spec's Section 2:

1. Read the Rust module + its tests on oq-1 in `sidequest-api/crates/<crate>/src/` and `sidequest-api/crates/<crate>/tests/`.
2. Port tests first to pytest. Verify RED (ImportError).
3. Port production code. Verify GREEN.
4. OTEL parity check for modules that emit spans (Story 41-4 + wherever spans are emitted).
5. Coverage gate: Python test count ≥ Rust test count for that crate.

Test names are preserved verbatim. Struct/field names are preserved verbatim. Translation rules are in the top-of-document Translation Key.

---

## Story 41-1: Port `sidequest.protocol`

**Goal:** `sidequest.protocol` contains every `MessageType`, every payload type, and the discriminated-union `GameMessage`. Byte-identical wire parity against captured Rust fixtures.

**Workflow:** tdd.

**Branch:** `feat/41-1-protocol` off `develop` in `sidequest-server`.

**Rust source:** `sidequest-api/crates/sidequest-protocol/src/`. Roughly 6.3k LOC per CLAUDE.md.

### Task 1: Capture Rust oracle fixtures for Phase 1 messages

**Files:**
- Create: `sidequest-server/scripts/capture_wire_fixture.py`
- Create: `sidequest-server/tests/protocol/fixtures/connect_handshake.json`
- Create: `sidequest-server/tests/protocol/fixtures/player_action_narration.json`

- [ ] **Step 1: Start the Rust server on oq-2 at a non-default port**

From a terminal:
```bash
cd /Users/keithavery/Projects/oq-2
SIDEQUEST_PORT=8090 just api-run &
```

- [ ] **Step 2: Write the capture harness**

```python
"""Harness to capture WebSocket wire fixtures from the Rust reference server.

Usage:
    python scripts/capture_wire_fixture.py connect_handshake > tests/protocol/fixtures/connect_handshake.json
    python scripts/capture_wire_fixture.py player_action_narration > tests/protocol/fixtures/player_action_narration.json

Each fixture records the full {sent: [...], received: [...]} exchange.
"""

from __future__ import annotations

import asyncio
import json
import sys

import websockets

ORACLE_URL = "ws://127.0.0.1:8090/ws"

SCENARIOS: dict[str, list[dict]] = {
    "connect_handshake": [
        # Empty — just connect and capture whatever handshake the server sends.
    ],
    "player_action_narration": [
        {
            "type": "PLAYER_ACTION",
            "payload": {"action": "I look around the tavern."},
            "player_id": "test-player-1",
        },
    ],
}


async def capture(scenario: str) -> dict:
    sent: list[dict] = []
    received: list[dict] = []

    async with websockets.connect(ORACLE_URL) as ws:
        for msg in SCENARIOS[scenario]:
            sent.append(msg)
            await ws.send(json.dumps(msg))
        # Drain any messages the server sends (up to 5 seconds)
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                received.append(json.loads(msg))
        except asyncio.TimeoutError:
            pass

    return {"scenario": scenario, "sent": sent, "received": received}


if __name__ == "__main__":
    scenario = sys.argv[1]
    result = asyncio.run(capture(scenario))
    print(json.dumps(result, indent=2, sort_keys=True))
```

- [ ] **Step 3: Run the harness and commit the fixtures**

```bash
cd /Users/keithavery/Projects/oq-1/sidequest-server
mkdir -p tests/protocol/fixtures
python scripts/capture_wire_fixture.py connect_handshake > tests/protocol/fixtures/connect_handshake.json
python scripts/capture_wire_fixture.py player_action_narration > tests/protocol/fixtures/player_action_narration.json
```

- [ ] **Step 4: Commit the harness + fixtures**

```bash
git add scripts/capture_wire_fixture.py tests/protocol/fixtures/
git commit -m "chore(41-1): capture Rust-oracle wire fixtures for Phase 1 protocol"
```

### Task 2: Port protocol tests (RED)

**Files:**
- Create: `sidequest-server/tests/protocol/__init__.py` (empty)
- Create: `sidequest-server/tests/protocol/test_messages.py`

- [ ] **Step 1: Read the Rust protocol tests**

Source files:
- `sidequest-api/crates/sidequest-protocol/src/lib.rs` (public surface)
- Any `mod tests` blocks inside the crate's src/ files
- `sidequest-api/crates/sidequest-protocol/tests/` (integration tests)

List every test function name; each one becomes a Python test.

- [ ] **Step 2: Write one pytest function per Rust test, verbatim names**

For each Rust test `fn test_foo_does_bar()`, write:

```python
def test_foo_does_bar():
    # Translate assertions per the Translation Key.
    ...
```

Include the fixture-based tests:

```python
import json
from pathlib import Path

import pytest

from sidequest.protocol import GameMessage


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text())


def test_connect_handshake_fixture_parses():
    """Every message from the Rust handshake can be parsed by Python GameMessage."""
    fixture = _load_fixture("connect_handshake")
    for msg in fixture["received"]:
        parsed = GameMessage.model_validate(msg)
        assert parsed is not None


def test_player_action_narration_fixture_roundtrip():
    """Sent + received messages round-trip losslessly through pydantic."""
    fixture = _load_fixture("player_action_narration")
    for msg in fixture["sent"] + fixture["received"]:
        parsed = GameMessage.model_validate(msg)
        reserialized = json.loads(parsed.model_dump_json())
        assert reserialized == msg
```

- [ ] **Step 3: Run tests, verify RED**

```bash
pytest tests/protocol/test_messages.py -v
```

Expected: `ImportError: cannot import name 'GameMessage' from 'sidequest.protocol'`. This is the RED signal — do not proceed until this error type appears.

- [ ] **Step 4: Commit the failing tests**

```bash
git add tests/protocol/
git commit -m "test(41-1): port protocol tests from Rust (RED)"
```

### Task 3: Port `MessageType` enum and shared types (GREEN step 1)

**Files:**
- Create: `sidequest-server/sidequest/protocol/types.py`

- [ ] **Step 1: Read the Rust `MessageType` enum**

Source: find the `enum MessageType` definition in `sidequest-protocol/src/`.

- [ ] **Step 2: Write the Python equivalent as `str`-enum**

```python
"""Shared protocol types."""

from __future__ import annotations

from enum import Enum


class MessageType(str, Enum):
    """Every recognized GameMessage kind. Values match Rust serde repr verbatim."""

    # Port every variant from the Rust enum here, preserving serde `rename = "..."` attrs.
    # Example:
    PLAYER_ACTION = "PLAYER_ACTION"
    NARRATION = "NARRATION"
    NARRATION_CHUNK = "NARRATION_CHUNK"
    NARRATION_END = "NARRATION_END"
    SESSION_EVENT = "SESSION_EVENT"
    ERROR = "ERROR"
    # ... continue for every variant in the Rust enum
```

- [ ] **Step 3: Commit**

```bash
git add sidequest/protocol/types.py
git commit -m "feat(41-1): port MessageType enum"
```

### Task 4: Port payload models and discriminated union (GREEN step 2)

**Files:**
- Create: `sidequest-server/sidequest/protocol/messages.py`

- [ ] **Step 1: Read the Rust payload structs**

For each `MessageType` variant, the Rust tree defines a payload struct. Enumerate them (e.g., `PlayerActionPayload`, `NarrationPayload`, etc.). Each struct's fields port to pydantic `BaseModel` fields per the Translation Key.

- [ ] **Step 2: Write each payload model as a pydantic `BaseModel`**

Pattern:

```python
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from sidequest.protocol.types import MessageType


class PlayerActionPayload(BaseModel):
    """Port of sidequest_protocol::PlayerActionPayload."""
    type: Literal[MessageType.PLAYER_ACTION] = MessageType.PLAYER_ACTION
    action: str
    # Add every field from the Rust struct, preserving field names.


class NarrationPayload(BaseModel):
    """Port of sidequest_protocol::NarrationPayload."""
    type: Literal[MessageType.NARRATION] = MessageType.NARRATION
    text: str
    # Add every field from the Rust struct.


# ... one BaseModel per MessageType variant


# The discriminated union
Payload = Annotated[
    Union[
        PlayerActionPayload,
        NarrationPayload,
        # ... every payload
    ],
    Field(discriminator="type"),
]


class GameMessage(BaseModel):
    """Port of sidequest_protocol::GameMessage."""
    type: MessageType
    payload: Payload
    player_id: str = ""
```

- [ ] **Step 3: Re-export from `__init__.py`**

`sidequest/protocol/__init__.py`:
```python
from sidequest.protocol.messages import GameMessage
from sidequest.protocol.types import MessageType

__all__ = ["GameMessage", "MessageType"]
```

- [ ] **Step 4: Run tests, verify GREEN**

```bash
pytest tests/protocol/ -v
```

Expected: every test passes, including the fixture round-trip tests.

- [ ] **Step 5: Verify coverage gate**

```bash
# Rust test count
cargo test -p sidequest-protocol 2>&1 | grep "test result" | tail -1
# Python test count
pytest tests/protocol/ --collect-only -q | tail -1
```

Python count must be ≥ Rust count. If not, go back and add the missing tests before proceeding.

- [ ] **Step 6: Commit**

```bash
git add sidequest/protocol/
git commit -m "feat(41-1): port GameMessage + payloads with pydantic discriminated unions"
```

### Task 5: Mark Story 41-1 complete

- [ ] **Step 1: Push + PR**

From a terminal:
```bash
git push -u origin feat/41-1-protocol
gh pr create --base develop --title "Story 41-1: Port sidequest.protocol" --body "ADR-082 Phase 1 Story 1 — protocol ported to pydantic discriminated unions with Rust-oracle fixture parity."
```

- [ ] **Step 2: Merge, verify develop is green**

```bash
gh pr merge --squash
git checkout develop && git pull
just server-test
```

**DoD:** All protocol tests pass. Fixture round-trip is byte-identical. Python test count ≥ Rust test count.

---

## Story 41-2: Port `sidequest.genre` with `LayeredMerge` consolidation

**Goal:** Genre pack loader, pydantic models for layered entities, and the authorized `LayeredMerge` consolidation that replaces the `genre-layered-derive` proc-macro expansion.

**Workflow:** tdd.

**Branch:** `feat/41-2-genre-with-layered-merge` off `develop` in `sidequest-server`.

**Rust source:** `sidequest-api/crates/sidequest-genre/src/` + `sidequest-api/crates/sidequest-genre-layered-derive/src/`. Roughly 5.2k LOC in the main crate.

### Task 1: Identify all `#[derive(Layered)]` types

- [ ] **Step 1: Inventory the layered types**

```bash
grep -rn "#\[derive(.*Layered.*)\]" /Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-genre/src/
```

For each hit, record:
- Type name (e.g., `Archetype`, `Axis`, `Lore`)
- Source file
- Every field with a `#[layer(merge = "...")]` attribute

Create a scratch file `docs/port-notes/genre-layered-inventory.md` listing each type and its field-merge-strategy map. This file is a working doc and gets committed separately at the end of Task 1.

- [ ] **Step 2: Commit the inventory**

```bash
git add docs/port-notes/genre-layered-inventory.md
git commit -m "docs(41-2): inventory of #[derive(Layered)] types in sidequest-genre"
```

### Task 2: Port `LayeredMerge` tests (RED)

**Files:**
- Create: `sidequest-server/tests/genre/__init__.py` (empty)
- Create: `sidequest-server/tests/genre/test_layered_merge.py`

- [ ] **Step 1: Write tests for each of the four merge strategies**

```python
"""Tests for the LayeredMerge base class (the genre consolidation)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import Field

from sidequest.genre.resolver import LayeredMerge


class _Sample(LayeredMerge):
    name: str = Field(default="", json_schema_extra={"merge": "replace"})
    tags: list[str] = Field(default_factory=list, json_schema_extra={"merge": "append"})


class _NestedSample(LayeredMerge):
    header: _Sample = Field(
        default_factory=_Sample,
        json_schema_extra={"merge": "deep_merge"},
    )


def test_replace_strategy_takes_other_value():
    a = _Sample(name="base")
    b = _Sample(name="override")
    assert a.merge(b).name == "override"


def test_replace_strategy_takes_other_value_even_when_empty():
    a = _Sample(name="base")
    b = _Sample(name="")
    assert a.merge(b).name == ""


def test_append_strategy_extends_list():
    a = _Sample(tags=["one", "two"])
    b = _Sample(tags=["three"])
    assert a.merge(b).tags == ["one", "two", "three"]


def test_deep_merge_strategy_recurses():
    a = _NestedSample(header=_Sample(name="base", tags=["x"]))
    b = _NestedSample(header=_Sample(name="override", tags=["y"]))
    result = a.merge(b)
    assert result.header.name == "override"
    assert result.header.tags == ["x", "y"]


def test_culture_final_strategy():
    """Port culture_final semantics from Rust verbatim — see Rust resolver/load.rs."""
    # Implementation matches what Rust does. Read the Rust strategy logic
    # before writing this test; assert identical behavior.
    pass  # Filled in once Rust culture_final behavior is confirmed.
```

Plus one per-type wiring test (per Section 4 of the spec: "test_<TypeName>_layered_merge_fields_declared"). For each type in the genre-layered-inventory:

```python
def test_archetype_layered_merge_fields_declared():
    """Every field on Archetype has a declared merge strategy (no silent defaults)."""
    from sidequest.genre.models.archetype import Archetype

    for field_name, field_info in Archetype.model_fields.items():
        extra = field_info.json_schema_extra or {}
        assert "merge" in extra, (
            f"Archetype.{field_name} has no merge strategy declared. "
            f"Add Field(json_schema_extra={{'merge': 'replace'}}) or similar."
        )
```

- [ ] **Step 2: Run, verify RED**

```bash
pytest tests/genre/test_layered_merge.py -v
```

Expected: `ImportError` on `from sidequest.genre.resolver import LayeredMerge`.

- [ ] **Step 3: Commit**

```bash
git add tests/genre/
git commit -m "test(41-2): LayeredMerge strategy tests (RED)"
```

### Task 3: Implement `LayeredMerge` (GREEN)

**Files:**
- Create: `sidequest-server/sidequest/genre/resolver.py`

- [ ] **Step 1: Write the base class per the strategy spec's Section 4**

```python
"""Layered genre-pack resolution — base → genre → world merge.

Replaces the Rust #[derive(Layered)] proc-macro with a single runtime
base class that reads field-level merge strategies from pydantic Field
metadata.
"""

from __future__ import annotations

from typing import Any, Self, get_args, get_origin

from pydantic import BaseModel


def _apply_strategy(strategy: str, self_val: Any, other_val: Any) -> Any:
    """Apply a merge strategy to two field values."""
    if strategy == "replace":
        return other_val
    if strategy == "append":
        return list(self_val) + list(other_val)
    if strategy == "deep_merge":
        if isinstance(self_val, LayeredMerge) and isinstance(other_val, LayeredMerge):
            return self_val.merge(other_val)
        raise TypeError(
            f"deep_merge requires both values to be LayeredMerge instances; "
            f"got {type(self_val).__name__} and {type(other_val).__name__}"
        )
    if strategy == "culture_final":
        # Port from Rust resolver/load.rs — read the Rust impl to match semantics.
        return _culture_final(self_val, other_val)
    raise ValueError(f"Unknown merge strategy: {strategy!r}")


def _culture_final(self_val: Any, other_val: Any) -> Any:
    """Port of the Rust culture_final strategy. See sidequest-genre/src/resolver/load.rs."""
    # Filled in after reading the Rust impl.
    raise NotImplementedError("culture_final: port pending from Rust resolver")


class LayeredMerge(BaseModel):
    """Mixin for pydantic models participating in base → genre → world layering.

    Field merge behavior is declared via Field metadata:
        name: str = Field(default="", json_schema_extra={"merge": "replace"})
        tags: list[str] = Field(default_factory=list, json_schema_extra={"merge": "append"})
        stats: StatBlock = Field(default_factory=StatBlock, json_schema_extra={"merge": "deep_merge"})

    Every field MUST declare a merge strategy. Omitting one is a programming
    error detected by the per-type wiring test (test_<TypeName>_layered_merge_fields_declared).
    """

    def merge(self, other: Self) -> Self:
        """Return a new instance with fields merged per each field's declared strategy."""
        merged: dict[str, Any] = {}
        for field_name, field_info in self.model_fields.items():
            extra = field_info.json_schema_extra or {}
            strategy = extra.get("merge", "replace")
            self_val = getattr(self, field_name)
            other_val = getattr(other, field_name)
            merged[field_name] = _apply_strategy(strategy, self_val, other_val)
        return type(self)(**merged)
```

- [ ] **Step 2: Read the Rust `culture_final` strategy**

Read `sidequest-api/crates/sidequest-genre/src/resolver/load.rs` and any linked implementation. Port the semantics into `_culture_final` in `resolver.py`. Add a test asserting the ported behavior matches a known Rust case (use a small fixture if the behavior is data-dependent).

- [ ] **Step 3: Run tests, verify GREEN on the strategy tests**

```bash
pytest tests/genre/test_layered_merge.py -v
```

The per-type wiring tests will still fail (no types yet); that's expected.

- [ ] **Step 4: Commit**

```bash
git add sidequest/genre/resolver.py
git commit -m "feat(41-2): LayeredMerge base class (replaces #[derive(Layered)] proc-macro)"
```

### Task 4: Port layered model types

**Files:**
- For each type in the inventory from Task 1:
  - Create: `sidequest-server/sidequest/genre/models/<type>.py`
  - The per-type wiring test in `tests/genre/test_layered_merge.py` must pass.

**Note on scope:** The Rust tree has many `Layered` types (likely 5–15). Each is its own sub-task-pair (RED → GREEN) following the same pattern. Rather than enumerating them here, execute per-type as follows for each:

For each type `<T>`:

- [ ] **Step 1 (RED):** Write any per-field-behavior tests from the Rust tree's test file for that type to `tests/genre/test_models/test_<t>.py`. Run, confirm ImportError.

- [ ] **Step 2 (GREEN):** Port the Rust struct to a pydantic `BaseModel` subclassing `LayeredMerge`:

```python
# Example shape for sidequest/genre/models/archetype.py
from __future__ import annotations

from pydantic import Field

from sidequest.genre.resolver import LayeredMerge


class Archetype(LayeredMerge):
    """Port of sidequest_genre::Archetype."""

    name: str = Field(default="", json_schema_extra={"merge": "replace"})
    # Port every field. Declare merge strategy per the original #[layer(merge = "...")] annotation.
```

- [ ] **Step 3:** Run the wiring test for this type; it must pass.

- [ ] **Step 4:** Commit per type: `feat(41-2): port <T> as LayeredMerge model`.

### Task 5: Port the YAML loader and cache

**Files:**
- Create: `sidequest-server/sidequest/genre/loader.py`
- Create: `sidequest-server/sidequest/genre/cache.py`
- Create: `sidequest-server/sidequest/genre/error.py`
- Create: `sidequest-server/tests/genre/test_loader.py`

- [ ] **Step 1: Port loader tests from Rust (RED)**

Read `sidequest-api/crates/sidequest-genre/src/loader.rs` (and any tests). Port every `fn test_loader_*` to pytest.

- [ ] **Step 2: Port the loader implementation (GREEN)**

The loader reads YAML files from a genre pack directory, instantiates the corresponding pydantic model, and drives base → genre → world merges. Use `pyyaml` for parsing.

Key behaviors to preserve:
- File layout: `base/<type>.yaml`, `genres/<genre>/<type>.yaml`, `worlds/<world>/<type>.yaml` — the exact path shape the Rust loader expects. Read the Rust `loader.rs` for the specifics.
- Merge order: base first → genre override → world override. Drive through `LayeredMerge.merge`.
- Missing-file handling: fail loudly per CLAUDE.md. No silent fallbacks.

- [ ] **Step 3: Port the cache (GREEN)**

The Rust tree has a `cache.rs`. It likely memoizes loaded + resolved packs. Port as a `functools.lru_cache` or module-level dict-based cache.

- [ ] **Step 4: Port the error types**

Rust `error.rs` defines genre-loader error variants. Port each to a Python exception subclass.

- [ ] **Step 5: Verify the loader round-trips a real genre pack**

Add a smoke test that loads `caverns_and_claudes` from `sidequest-content/genre_packs/` and asserts the resolved pack is structurally well-formed (at least one archetype, at least one axis).

```python
def test_loader_resolves_caverns_and_claudes(content_dir):
    from sidequest.genre.loader import load_genre_pack
    pack = load_genre_pack(content_dir / "genre_packs" / "caverns_and_claudes")
    assert len(pack.archetypes) > 0
```

- [ ] **Step 6: Verify coverage gate**

```bash
cargo test -p sidequest-genre 2>&1 | grep "test result" | tail -1
pytest tests/genre/ --collect-only -q | tail -1
```

Python count ≥ Rust count.

- [ ] **Step 7: Commit**

```bash
git add sidequest/genre/ tests/genre/
git commit -m "feat(41-2): port YAML loader, cache, error types for sidequest.genre"
```

### Task 6: Mark Story 41-2 complete

- [ ] **Step 1: Push + PR + merge** (same pattern as 41-1).

**DoD:** All genre tests pass. Real genre pack loads. Every `Layered` type has a wiring test that asserts declared merge strategies. Python test count ≥ Rust test count.

---

## Story 41-3: Port `sidequest.game` minimal slice

**Goal:** Just enough of `sidequest.game` to support a narration turn: `Character`, `Session`, `GameState`, and a minimal `commands` enum for narrator dispatch. Combat/dice/chase/scenario/advancement are NOT in scope for this story — those are Phases 2–6.

**Workflow:** tdd.

**Branch:** `feat/41-3-game-minimal` off `develop`.

**Rust source:** `sidequest-api/crates/sidequest-game/src/` — specifically `character.rs`, `session.rs` or `state.rs`, and `commands.rs`. ~29.3k LOC total in the crate, but Phase 1 touches maybe 2k LOC.

### Task 1: Define the Phase 1 slice boundary

- [ ] **Step 1: Inventory the modules the narrator touches**

Trace from `sidequest-agents/src/narrator.rs` (which the narrator agent port in Story 41-5 will use). Every `use sidequest_game::X::Y` it pulls in gets listed.

Expect (to confirm by inspection): `Character`, `Session`, `GameState`, plus maybe `NarrativeSheet` or `JournalEntry`. Read the Rust narrator and make the definitive list.

Write this to `docs/port-notes/game-phase1-slice.md` and commit:

```bash
git add docs/port-notes/game-phase1-slice.md
git commit -m "docs(41-3): Phase 1 slice boundary for sidequest.game"
```

### Task 2: Port Character (RED → GREEN)

**Files:**
- Create: `sidequest-server/tests/game/__init__.py` (empty)
- Create: `sidequest-server/tests/game/test_character.py`
- Create: `sidequest-server/sidequest/game/character.py`

- [ ] **Step 1: Port character tests from Rust (RED)**

Read `sidequest-api/crates/sidequest-game/src/character.rs` and any `mod tests`. Port every test to pytest. Run, confirm ImportError.

- [ ] **Step 2: Port Character pydantic model (GREEN)**

```python
# sidequest/game/character.py
from __future__ import annotations

from pydantic import BaseModel, Field

# Port every field from Rust struct Character. Preserve field names.
# If Character composes sub-structs (stats, equipment, etc.), port those too
# as nested BaseModels. Defer any Phase 2+ fields (combat stats, dice pools)
# behind a "not in Phase 1 slice" comment — DO NOT port them now.


class Character(BaseModel):
    """Port of sidequest_game::Character (Phase 1 slice — narrator-relevant fields only)."""

    id: str
    name: str
    # ... Phase 1 fields only
```

- [ ] **Step 3: Verify coverage note**

Document in `docs/port-notes/game-phase1-slice.md` which Character fields were deferred to later phases and why.

- [ ] **Step 4: Commit**

```bash
git add sidequest/game/character.py tests/game/test_character.py
git commit -m "feat(41-3): port Character (Phase 1 slice) from sidequest-game"
```

### Task 3: Port Session and GameState

Same RED → GREEN pattern.

**Files:**
- Create: `sidequest-server/tests/game/test_session.py`
- Create: `sidequest-server/sidequest/game/session.py`

- [ ] **Step 1: Port session tests (RED)**

Read the Rust session/state tests; port to pytest.

- [ ] **Step 2: Implement Session and GameState (GREEN)**

Preserve the Rust struct shape. Note: if the Rust `GameState` is large with many sub-aggregates, port ONLY the aggregates that narrator needs in Phase 1. Others get a comment:

```python
# Phase 1 slice: the following sub-aggregates are deferred to later phases:
# - combat: Phase 3 (Story 41-11)
# - chase: Phase 4
# - ...
```

- [ ] **Step 3: Commit**

```bash
git add sidequest/game/session.py tests/game/test_session.py
git commit -m "feat(41-3): port Session + GameState (Phase 1 slice)"
```

### Task 4: Port commands enum

**Files:**
- Create: `sidequest-server/sidequest/game/commands.py`
- Create: `sidequest-server/tests/game/test_commands.py`

- [ ] **Step 1: Port commands tests (RED)**

- [ ] **Step 2: Port commands enum (GREEN)**

The narrator dispatch needs a small command enum. Port only the variants that Phase 1 uses; comment the rest as deferred.

- [ ] **Step 3: Commit**

```bash
git add sidequest/game/commands.py tests/game/test_commands.py
git commit -m "feat(41-3): port commands enum (Phase 1 variants only)"
```

### Task 5: Save/load session (SQLite round-trip)

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py` — add `save_to_db()` / `load_from_db()` methods
- Create: `sidequest-server/tests/game/test_session_persistence.py`

- [ ] **Step 1: Port session persistence tests (RED)**

Read the Rust save-load tests. Port to pytest, using pydantic's `model_dump_json()` for serialization and `model_validate_json()` for deserialization — stored as a `state_json` TEXT column in SQLite.

- [ ] **Step 2: Implement save/load (GREEN)**

Use stdlib `sqlite3`. Schema matches the Rust `rusqlite` schema byte-for-byte — same table names, same column names, same column types. The save format is load-bearing for save-file compatibility per the strategy spec's non-goals ("existing saves from Rust should load on Python").

- [ ] **Step 3: Smoke test with a real save file**

```python
def test_loads_real_rust_save_file(tmp_save_dir):
    """One of the spec's 41-7 checks ported earlier for confidence."""
    import shutil
    real_save = Path.home() / ".sidequest" / "saves" / "caverns_and_claudes-tavern.db"
    if not real_save.exists():
        pytest.skip("no real save file available")
    shutil.copy(real_save, tmp_save_dir / "test.db")
    # Load via our session loader
    from sidequest.game.session import Session
    session = Session.load_from_db(tmp_save_dir / "test.db")
    assert session.id
    assert session.characters
```

- [ ] **Step 4: Commit**

```bash
git add sidequest/game/session.py tests/game/test_session_persistence.py
git commit -m "feat(41-3): session SQLite persistence — Rust save-file compatible"
```

### Task 6: Mark Story 41-3 complete

Push + PR + merge. Document deferred fields in `docs/port-notes/game-phase1-slice.md` (one entry per deferred aggregate/field).

**DoD:** Character/Session/GameState/commands pass their tests. Real Rust save files load on Python. Deferred-field inventory committed.

---

## Story 41-4: Port `sidequest.telemetry`

**Goal:** OTEL span catalog for Phase 1 modules. Every span emitted by narrator, session, genre-load, character-fetch has a named constant and a helper.

**Workflow:** tdd.

**Branch:** `feat/41-4-telemetry` off `develop`.

**Rust source:** `sidequest-api/crates/sidequest-telemetry/src/`. ~290 LOC — small crate.

### Task 1: Port span name constants

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans.py`
- Create: `sidequest-server/tests/telemetry/__init__.py` (empty)
- Create: `sidequest-server/tests/telemetry/test_spans.py`

- [ ] **Step 1: Inventory Rust span names**

```bash
grep -rn 'info_span!\|tracing::span!' /Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-telemetry/src/
grep -rn 'info_span!\|tracing::span!' /Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-server/src/
grep -rn 'info_span!\|tracing::span!' /Users/keithavery/Projects/oq-1/sidequest-api/crates/sidequest-agents/src/
```

Collect every `info_span!("name", ...)` name string. These become Python constants.

- [ ] **Step 2: Write tests (RED)**

```python
def test_all_phase1_span_names_are_defined():
    """Every span name the Rust tree emits in Phase 1 modules has a Python constant."""
    from sidequest.telemetry.spans import (
        SPAN_NARRATOR_TURN,
        SPAN_SESSION_LOAD,
        SPAN_SESSION_SAVE,
        SPAN_GENRE_LOAD,
        SPAN_CHARACTER_FETCH,
        SPAN_CLAUDE_SUBPROCESS,
        # ... one per Rust span
    )
    assert SPAN_NARRATOR_TURN == "narrator.turn"
    # ... assert every constant equals its Rust literal exactly
```

- [ ] **Step 3: Implement `spans.py` (GREEN)**

```python
"""OTEL span name constants.

One constant per span emitted by Phase 1 modules. Values are byte-identical
to the Rust tree's info_span!("...") name strings.
"""

SPAN_NARRATOR_TURN = "narrator.turn"
SPAN_SESSION_LOAD = "session.load"
SPAN_SESSION_SAVE = "session.save"
SPAN_GENRE_LOAD = "genre.load"
SPAN_CHARACTER_FETCH = "character.fetch"
SPAN_CLAUDE_SUBPROCESS = "claude.subprocess"
# ... every Rust span, byte-for-byte name match
```

- [ ] **Step 4: Commit**

```bash
git add sidequest/telemetry/spans.py tests/telemetry/test_spans.py
git commit -m "feat(41-4): port OTEL span name catalog for Phase 1"
```

### Task 2: OTEL parity harness

**Files:**
- Create: `sidequest-server/scripts/capture_otel_spans.py`
- Create: `sidequest-server/tests/telemetry/fixtures/phase1_spans.json`

- [ ] **Step 1: Capture Rust OTEL output for a known scenario**

Run the Rust server configured to emit to a JSON OTEL exporter for one known narration scenario. Save the span tree to `tests/telemetry/fixtures/phase1_spans.json`.

- [ ] **Step 2: Write the parity-check test**

```python
def test_python_narrator_turn_spans_match_rust_structure():
    """Python OTEL output for one narration turn has structurally identical spans to Rust."""
    # Capture Python spans for the same scenario (use an in-memory exporter).
    # Normalize both: sort by (name, parent), drop runtime-identity values (IDs, timestamps).
    # Assert structural equality.
    ...
```

Per the strategy spec's Section 2 Step 5, parity is defined structurally: names + parent/child + attribute keys match; values match where they reflect domain state but may differ for runtime-identity values.

- [ ] **Step 3: Commit**

```bash
git add scripts/capture_otel_spans.py tests/telemetry/fixtures/
git commit -m "test(41-4): OTEL parity harness + Rust fixture for Phase 1 spans"
```

### Task 3: Mark Story 41-4 complete

Push + PR + merge.

**DoD:** Every Phase 1 span has a Python constant matching its Rust name. OTEL parity test runs green against captured Rust output.

---

## Story 41-5: Port `sidequest.agents.narrator`

**Goal:** The narrator agent — Claude subprocess orchestration, prompt construction, and the turn pipeline that takes a `PLAYER_ACTION` and returns `NARRATION`.

**Workflow:** tdd.

**Branch:** `feat/41-5-narrator` off `develop`.

**Rust source:** `sidequest-api/crates/sidequest-agents/src/`, specifically `claude_agent.rs`, `narrator.rs`, `prompt_builder.rs` (or whatever the Rust naming is — verify on inspection). ~10.3k LOC in the crate; Phase 1 touches maybe 2-3k.

### Task 1: Port Claude subprocess runner

**Files:**
- Create: `sidequest-server/sidequest/agents/claude_agent.py`
- Create: `sidequest-server/tests/agents/__init__.py` (empty)
- Create: `sidequest-server/tests/agents/test_claude_agent.py`

- [ ] **Step 1: Read the Rust `claude_agent.rs`**

Understand the subprocess invocation: exact command args, env vars, stdin/stdout/stderr handling, shutdown/cancellation behavior.

- [ ] **Step 2: Port tests (RED)**

Include at least one test that mocks `claude -p` with a stubbed subprocess (a shell script that echoes a fixed response). Do NOT call the real Claude CLI in the default test suite — memory `feedback_no_live_llm_tests.md`: mock, don't call.

```python
import asyncio
from pathlib import Path

import pytest


@pytest.fixture
def fake_claude(tmp_path: Path) -> Path:
    """A fake `claude` executable that echoes stdin to stdout."""
    fake = tmp_path / "claude"
    fake.write_text("#!/usr/bin/env bash\ncat\n")
    fake.chmod(0o755)
    return fake


async def test_claude_agent_runs_subprocess(fake_claude):
    from sidequest.agents.claude_agent import ClaudeAgent

    agent = ClaudeAgent(claude_binary=fake_claude)
    result = await agent.run(prompt="Hello, narrator.")
    assert "Hello, narrator." in result
```

- [ ] **Step 3: Implement `ClaudeAgent` (GREEN)**

```python
"""Claude CLI subprocess runner — port of sidequest-agents::claude_agent."""

from __future__ import annotations

import asyncio
from pathlib import Path

from opentelemetry import trace

from sidequest.telemetry.spans import SPAN_CLAUDE_SUBPROCESS


class ClaudeAgent:
    """Runs `claude -p <prompt>` and returns stdout.

    Matches the Rust tokio::process::Command invocation exactly:
    same args, same env inheritance, same stdin handling.
    """

    def __init__(self, claude_binary: Path | str = "claude") -> None:
        self._claude_binary = str(claude_binary)

    async def run(self, prompt: str) -> str:
        """Invoke claude -p with the given prompt; return stdout."""
        tracer = trace.get_tracer("sidequest-server")
        with tracer.start_as_current_span(SPAN_CLAUDE_SUBPROCESS):
            proc = await asyncio.create_subprocess_exec(
                self._claude_binary,
                "-p",
                prompt,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(
                    f"claude exited {proc.returncode}: {stderr.decode()}"
                )
            return stdout.decode()
```

- [ ] **Step 4: Verify matches the Rust invocation**

Compare arg list + env handling against `sidequest-agents/src/claude_agent.rs`. If Rust passes extra args (e.g., `--output-format`, `--no-color`), port them.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/claude_agent.py tests/agents/test_claude_agent.py
git commit -m "feat(41-5): port ClaudeAgent subprocess runner"
```

### Task 2: Port prompt builder

**Files:**
- Create: `sidequest-server/sidequest/agents/prompt_builder.py`
- Create: `sidequest-server/tests/agents/test_prompt_builder.py`

- [ ] **Step 1: Read the Rust prompt builder**

The Rust tree likely has a `prompt_builder.rs` that assembles the narrator prompt from session state + character + recent history + genre tone. Port the assembly logic. Phase 1 needs only the narrator prompt; other agent prompts are deferred.

- [ ] **Step 2: Port tests (RED)**

Test against known inputs: "given character X, session state Y, action Z, the built prompt contains sections A, B, C in order." Use snapshot tests if the Rust tree uses them.

- [ ] **Step 3: Implement (GREEN)**

Preserve the Rust prompt structure byte-for-byte — prompt wording is load-bearing for narrator quality.

- [ ] **Step 4: Commit**

```bash
git add sidequest/agents/prompt_builder.py tests/agents/test_prompt_builder.py
git commit -m "feat(41-5): port narrator prompt builder"
```

### Task 3: Port the narrator agent turn pipeline

**Files:**
- Create: `sidequest-server/sidequest/agents/narrator.py`
- Create: `sidequest-server/tests/agents/test_narrator.py`

- [ ] **Step 1: Read the Rust narrator**

`sidequest-agents/src/narrator.rs` — the turn pipeline. Typical shape: takes `PLAYER_ACTION` + session + character → builds prompt → runs ClaudeAgent → parses response → emits `NARRATION`.

- [ ] **Step 2: Port tests (RED)**

```python
async def test_narrator_turn_produces_narration(fake_claude, content_dir):
    from sidequest.agents.narrator import NarratorAgent
    from sidequest.game.session import Session
    from sidequest.game.character import Character
    from sidequest.protocol.messages import PlayerActionPayload

    narrator = NarratorAgent(claude_binary=fake_claude)
    session = Session.create(genre_pack_dir=content_dir / "genre_packs" / "caverns_and_claudes")
    character = Character(id="c1", name="Rux")
    session.characters.append(character)

    action = PlayerActionPayload(action="I look around the tavern.")
    narration = await narrator.turn(session=session, character=character, action=action)

    assert narration.text  # non-empty
```

- [ ] **Step 3: Implement NarratorAgent (GREEN)**

Preserve the Rust pipeline: build prompt → claude → parse → emit span → return narration. Every state transition gets an OTEL span (per CLAUDE.md "Every backend fix that touches a subsystem MUST add OTEL watcher events").

- [ ] **Step 4: Verify OTEL emission**

Run the narrator test with OTEL parity harness enabled. Assert `SPAN_NARRATOR_TURN`, `SPAN_CLAUDE_SUBPROCESS` are emitted with correct parent/child.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/narrator.py tests/agents/test_narrator.py
git commit -m "feat(41-5): port narrator turn pipeline with OTEL spans"
```

### Task 4: Mark Story 41-5 complete

Push + PR + merge.

**DoD:** Narrator turn pipeline produces `NarrationPayload` from `PlayerActionPayload` + `Session` + `Character`. OTEL spans emitted. Claude subprocess mock works (no live Claude calls in tests).

---

## Story 41-6: Port `sidequest.server` (FastAPI + WebSocket + dispatch)

**Goal:** FastAPI app with `/ws` WebSocket endpoint. Connected client can send `PLAYER_ACTION`, get `NARRATION` back, session persists. Dispatch routing for Phase 1 message types only.

**Workflow:** tdd.

**Branch:** `feat/41-6-server` off `develop`.

**Rust source:** `sidequest-api/crates/sidequest-server/src/`. ~16k LOC. Phase 1 touches maybe 3-4k — the core WebSocket handler, session_handler, and dispatch for `PLAYER_ACTION`.

### Task 1: Port WebSocket handler

**Files:**
- Create: `sidequest-server/sidequest/server/websocket.py`
- Create: `sidequest-server/tests/server/__init__.py` (empty)
- Create: `sidequest-server/tests/server/test_websocket.py`

- [ ] **Step 1: Read the Rust WebSocket handler**

`sidequest-server/src/` contains an `axum::extract::ws` handler. Port the message-loop shape: receive → parse GameMessage → dispatch → respond.

- [ ] **Step 2: Port tests (RED)**

FastAPI's `TestClient` supports WebSocket testing via `client.websocket_connect("/ws")`. Write one test per message type the Phase 1 dispatch handles (primarily `PLAYER_ACTION`).

- [ ] **Step 3: Implement the handler (GREEN)**

```python
# sidequest/server/websocket.py
from __future__ import annotations

import json

from fastapi import FastAPI, WebSocket

from sidequest.protocol import GameMessage
from sidequest.server.dispatch import dispatch


def register(app: FastAPI) -> None:
    """Register the /ws WebSocket endpoint on the FastAPI app."""

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                raw = await ws.receive_text()
                msg = GameMessage.model_validate_json(raw)
                response = await dispatch(msg)
                if response is not None:
                    await ws.send_text(response.model_dump_json())
        except Exception as exc:
            # TODO(41-6 task N): structured error response
            raise
```

- [ ] **Step 4: Wire into `app.py`**

Modify `sidequest/server/app.py` to call `websocket.register(app)` in `create_app()`.

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/websocket.py sidequest/server/app.py tests/server/test_websocket.py
git commit -m "feat(41-6): /ws WebSocket endpoint with GameMessage parse + dispatch"
```

### Task 2: Port the dispatch router

**Files:**
- Create: `sidequest-server/sidequest/server/dispatch.py`
- Create: `sidequest-server/tests/server/test_dispatch.py`

- [ ] **Step 1: Read the Rust dispatch**

The Rust server has a dispatch-handler module (likely split across `dispatch/` per ADR-063). Phase 1 dispatch handles `PLAYER_ACTION` → narrator.

- [ ] **Step 2: Port tests (RED)**

Test: "dispatch of a PLAYER_ACTION invokes the narrator and returns a NarrationPayload."

- [ ] **Step 3: Implement (GREEN)**

```python
# sidequest/server/dispatch.py
from __future__ import annotations

from sidequest.agents.narrator import NarratorAgent
from sidequest.protocol import GameMessage, MessageType
from sidequest.server.session_handler import get_session_handler


_narrator = NarratorAgent()  # singleton — matches Rust's one-per-server pattern


async def dispatch(msg: GameMessage) -> GameMessage | None:
    """Route an inbound GameMessage to its handler; return a response message if any."""
    handler = get_session_handler(msg.player_id)
    if msg.type == MessageType.PLAYER_ACTION:
        narration = await _narrator.turn(
            session=handler.session,
            character=handler.character,
            action=msg.payload,
        )
        return GameMessage(
            type=MessageType.NARRATION,
            payload=narration,
            player_id=msg.player_id,
        )
    # Phase 1: only PLAYER_ACTION is dispatched. Everything else is Phase 2+.
    return None
```

- [ ] **Step 4: Commit**

```bash
git add sidequest/server/dispatch.py tests/server/test_dispatch.py
git commit -m "feat(41-6): dispatch router — Phase 1 routes PLAYER_ACTION to narrator"
```

### Task 3: Port session handler

**Files:**
- Create: `sidequest-server/sidequest/server/session_handler.py`

- [ ] **Step 1: Port session-handler tests (RED)**

The session handler manages per-connection state — the `Session` object, the `Character` being played, save file reference. Read Rust `session_handler.rs` and port its tests.

- [ ] **Step 2: Implement (GREEN)**

Preserve Rust's lifecycle: connect → load-or-create session → per-turn mutate → save on disconnect.

- [ ] **Step 3: Commit**

```bash
git add sidequest/server/session_handler.py tests/server/test_session_handler.py
git commit -m "feat(41-6): per-connection session handler with save/load"
```

### Task 4: End-to-end WebSocket test

**Files:**
- Create: `sidequest-server/tests/server/test_end_to_end.py`

- [ ] **Step 1: Write the E2E test**

```python
import json

import pytest
from fastapi.testclient import TestClient

from sidequest.server.app import create_app


@pytest.mark.e2e
def test_player_action_gets_narration_response(fake_claude, content_dir, monkeypatch):
    """End-to-end: connect, send PLAYER_ACTION, receive NARRATION."""
    # Use fake_claude to avoid hitting the real CLI.
    monkeypatch.setenv("SIDEQUEST_CLAUDE_BIN", str(fake_claude))
    # Point at a real genre pack.
    monkeypatch.setenv("SIDEQUEST_CONTENT_DIR", str(content_dir))

    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({
            "type": "PLAYER_ACTION",
            "payload": {
                "type": "PLAYER_ACTION",
                "action": "I look around the tavern.",
            },
            "player_id": "test-1",
        }))
        response = json.loads(ws.receive_text())
        assert response["type"] == "NARRATION"
        assert response["payload"]["text"]  # non-empty
```

- [ ] **Step 2: Run, verify GREEN**

```bash
pytest tests/server/test_end_to_end.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_end_to_end.py
git commit -m "test(41-6): E2E PLAYER_ACTION → NARRATION over WebSocket"
```

### Task 5: Mark Story 41-6 complete

Push + PR + merge.

**DoD:** `/ws` accepts `PLAYER_ACTION`, returns `NARRATION`. Session persists to SQLite. E2E test green with mocked Claude.

---

## Story 41-7: Phase 1 integration playtest + cut-over readiness

**Goal:** Run a full solo playtest against the Python server using real Claude (not mocked) and a real genre pack. Produce a cut-over readiness report.

**Workflow:** trivial.

**Branch:** `chore/41-7-phase1-playtest` off `main` on the orchestrator repo (because the report lands in `docs/` on the orchestrator).

**Repo:** orchestrator (this one).

### Task 1: Run the Python server against real Claude

- [ ] **Step 1: Start the Python server**

From a terminal:
```bash
cd /Users/keithavery/Projects/oq-1
just server-dev
```

Expected: server binds 127.0.0.1:8080.

- [ ] **Step 2: Start the UI pointed at the Python server**

```bash
cd sidequest-ui
VITE_SIDEQUEST_API_URL=ws://127.0.0.1:8080/ws npm run dev
```

- [ ] **Step 3: Connect, create a character, take 5 turns**

Use a real genre pack (`caverns_and_claudes` or whichever playgroup pack is current). Record:
- Connect succeeds: Y/N
- Character creation completes: Y/N
- Each turn returns narration within playable latency: Y/N per turn
- OTEL panel shows spans consistent with the Rust catalog: Y/N
- Save/reload works (quit mid-session, reload from disk): Y/N

### Task 2: Write the readiness report

**Files:**
- Create: `sidequest-server/docs/port/2026-04-MM-phase1-readiness-report.md` (MM = date of playtest)

- [ ] **Step 1: Write the report**

```markdown
# Phase 1 Cut-over Readiness Report

**Date:** <playtest date>
**Playtester:** Keith (solo dry-run) / playgroup session
**Genre pack:** <pack name>

## Pre-cut-over checklist (per strategy spec Section 5)

- [ ] Every Phase 1 ported test is green on the Python server.
- [ ] OTEL span parity verified for Phase 1 modules.
- [ ] A full playtest has been run and felt indistinguishable from Rust.
- [ ] Rust `develop` tip tagged `rust-final-<YYYYMMDD>`.

## Turn-by-turn notes

### Turn 1
- Action: ...
- Narration quality vs. Rust expectation: ...
- Latency: ...
- OTEL span presence: ...

### Turn 2
...

## Findings

| Finding | Severity | Decision |
|---|---|---|
| ... | Critical/Major/Minor | Fix before cut-over / Defer to stabilization / Accept |

## Recommendation

[ ] Ready to cut over now
[ ] Needs N fixes before cut-over (list below)
[ ] Defer cut-over — Phase 1 not yet at playable parity

## Next steps

- ...
```

- [ ] **Step 2: Fill in the report from the playtest**

- [ ] **Step 3: Commit**

```bash
git add docs/port/
git commit -m "docs(41-7): Phase 1 cut-over readiness report"
```

### Task 3: Decide cut-over

- [ ] **Step 1: Review the report with Keith**

The report is the decision artifact. Keith reviews it against the pre-cut-over checklist and decides:
- Cut over now (proceed to Story 41-CO)
- Fix issues first (file follow-up stories under Epic 41)
- Defer cut-over and continue Phase 2+ on the Python branch while Rust stays live

- [ ] **Step 2: If cut-over approved, file Story 41-CO**

```bash
pf sprint story add 41-CO "Cut-over to sidequest-server" --workflow trivial --repo orchestrator
```

The 41-CO story executes the cut-over PR per strategy spec Section 5.

**DoD:** Report committed. Decision made. If cut-over approved, Story 41-CO filed.

---

## Self-Review

**1. Spec coverage check.** Every section of the strategy spec covered by at least one task:
- Section 1 (strategy frame): Phases 0 and 1 are in the plan; Phases 2–7 deferred to follow-up plans.
- Section 2 (test porting discipline): each port story follows the RED → GREEN loop with coverage gate.
- Section 3 (Rust reference usage): Story 41-1 Task 1 captures oracle fixtures; later stories use frozen Rust as spec.
- Section 4 (genre consolidation): Story 41-2 Tasks 2–3 implement `LayeredMerge` with the per-type wiring test.
- Section 5 (cut-over mechanics): Story 41-7 is the readiness gate; Story 41-CO (future) executes the swap.
- Section 6 (sprint/story workflow): plan structure matches the spec's story breakdown (41-0 through 41-7).
- Section 7 (risks): the plan doesn't explicitly re-document risks, but each story's DoD + the coverage gate address the primary risks named.
- Section 8 (non-goals): the "Phase 1 slice only" comments in Stories 41-3 and 41-5 enforce the non-goal of over-porting.

**2. Placeholder scan:** 
- `docs/port-notes/genre-layered-inventory.md` in Story 41-2 Task 1 is meant to be generated from inspection — not a placeholder, a genuine working artifact filled in at execution time.
- `_culture_final` in `resolver.py` has a `raise NotImplementedError` that's explicit about pending Rust inspection — this is correct; Dev fills it in after reading the Rust source.
- Task 4 in Story 41-2 ("Port layered model types") doesn't enumerate every type — it says "for each type in the inventory," with the pattern shown. Acceptable given the inventory isn't known until Task 1 runs.
- Story 41-7 Task 2's report template has `<placeholder>` slots — those are *template* placeholders filled at playtest time, not plan placeholders.

**3. Type consistency check:**
- `GameMessage`, `MessageType`, `PlayerActionPayload`, `NarrationPayload` used consistently across Stories 41-1 (defined), 41-5 (consumed), 41-6 (dispatch).
- `LayeredMerge` defined in 41-2 Task 3, consumed in 41-2 Task 4.
- `Character`, `Session`, `GameState` defined in 41-3, consumed in 41-5 narrator and 41-6 session_handler.
- `NarratorAgent`, `ClaudeAgent` defined in 41-5, consumed in 41-6 dispatch.
- Span constants (`SPAN_NARRATOR_TURN`, etc.) defined in 41-4, consumed in 41-5 narrator + 41-5 claude_agent.

No obvious drift.

**4. Scope check:** This is one plan covering Phase 0 + Phase 1 (8 stories). Each story is self-contained with its own DoD. The plan appropriately defers Phases 2–7 to future plans. Within-scope.

Plan ready for execution.
