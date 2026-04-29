# Local DM Group E — LlmClient Abstraction + Ollama Backend + Training Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver ADR-073 Phases 1–3: generalise the existing `ClaudeLike` Protocol into a proper `LlmClient` abstraction with capability discovery, add an `OllamaClient` backend selected by env var, and ship the MLX-LM QLoRA training pipeline in `sidequest-daemon` that consumes Group D `TrainingPair` JSONL. Claude remains default; local backends are opt-in.

**Architecture:** Rename `ClaudeLike` → `LlmClient` in `sidequest/agents/claude_client.py` and add an `LlmCapabilities` dataclass + `capabilities()` method to the Protocol. Add a `backend: str` field to `ClaudeResponse` so telemetry tags the source. Introduce a new `sidequest/agents/ollama_client.py` implementing `LlmClient` against Ollama's `/api/generate` and `/api/chat`, with HTTP transport dependency-injected the same way `ClaudeClient` injects its subprocess spawner. Ollama has no server-side sessions, so the Ollama backend stores per-`session_id` chat history in an in-process dict and replays it on `send_with_session`. A tiny `sidequest/agents/llm_factory.py` reads `SIDEQUEST_LLM_BACKEND` (default `claude`) and returns the correct client. All call sites (`session_handler.py`, `orchestrator.py`, `local_dm.py`) continue taking `LlmClient` via DI — no runtime call-site changes. The QLoRA pipeline lives in `sidequest-daemon/sidequest_daemon/training/` as an offline CLI (`sidequest-train`), reads `~/.sidequest/corpus/**/*.jsonl`, and writes MLX safetensors adapters to `~/.sidequest/loras/<genre>/<base_model>-<timestamp>/`. Training uses `mlx-lm` (Apple Silicon, already-present MLX stack). Serving MLX-trained adapters through Ollama is explicitly out of scope.

**Tech Stack:** Python 3.12, pydantic, stdlib `urllib.request` for the Ollama HTTP client (no new runtime deps), pytest + pytest-asyncio. Daemon side adds `mlx-lm>=0.20` as an optional dep (gated behind an extra) and reuses the existing `mlx>=0.18` + `transformers` + `safetensors` stack.

**Reference spec:** `docs/adr/073-local-fine-tuned-model-architecture.md` (Phases 1–3). Ties back to `docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md` §4.3, §4.4 (corpus flow → fine-tune).

**Depends on:**

- Group D (landed as PR #41) — `sidequest/corpus/` ships `TrainingPair` schema + `~/.sidequest/corpus/mined/<timestamp>.jsonl` files. Phase 3 reads these directly.
- Existing `ClaudeLike` Protocol in `sidequest/agents/claude_client.py` (from story 40-1). Phase 1 renames it.
- No Group A/B/C/G dependency — Group E can run in parallel to any of them. Backend selection is a configuration knob, not a runtime contract change.

**Repos touched:**

- `sidequest-server/` — abstraction rename + Ollama client + factory + tests (branch `feat/local-dm-group-e-server`, targets `develop`)
- `sidequest-daemon/` — training pipeline + CLI (branch `feat/local-dm-group-e-daemon`, targets `develop`)

No `sidequest-content/`, `sidequest-ui/`, or orchestrator changes.

**Branch + worktrees:**

```
/Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-e
/Users/slabgorb/Projects/oq-1/sidequest-daemon/.worktrees/group-e
```

Each worktree is created off its repo's `develop`. Every subagent MUST `cd` to the absolute worktree path as its first bash call. Phase 1–2 tasks live in the server worktree. Phase 3 tasks live in the daemon worktree.

**Decisions locked (do not re-litigate):**

1. **Rename `ClaudeLike` → `LlmClient`; keep `ClaudeResponse` name.** The Protocol is now generic ("any LLM client"), so its name leaves Claude-specifics behind. `ClaudeResponse` is a data shape used pervasively; renaming it would churn ~30 files for no behavioural gain. Extend the shape with a `backend: str` field (default `"claude-cli"`) so OTEL spans can tag the producer. Per CLAUDE.md no-backcompat-shims: update every import directly — no type aliases left behind.
2. **Capabilities are a dataclass, not a dict.** `LlmCapabilities(supports_sessions: bool, supports_tools: bool, max_context_tokens: int, supports_streaming: bool)`. Frozen dataclass; cheap to construct; typed. Each client returns its own instance from `capabilities()`.
3. **Ollama HTTP uses `urllib.request` in a thread, not a new aiohttp/httpx dep.** Server runtime deps are intentionally slim (fastapi + uvicorn + pydantic + pyyaml + opentelemetry + websockets). Adding an HTTP library for one backend is scope creep. Blocking HTTP runs in `asyncio.to_thread(...)`. Transport is dependency-injected (`http_fn: Callable[[urllib.request.Request], http.client.HTTPResponse]`) the same way `ClaudeClient._spawn` is injected for tests.
4. **Ollama has no server-side sessions — history is client-side.** `OllamaClient` holds an internal `dict[str, list[ChatTurn]]` keyed by `session_id`. On `send_with_session(session_id=None, system_prompt=X)` it mints a new UUID, stores `[system, user]`, calls `/api/chat`, appends the assistant reply, returns the UUID as `response.session_id`. On `send_with_session(session_id=uuid, ...)` it replays the stored history + the new user message. Stored history is capped at `OLLAMA_HISTORY_CAP = 32` exchanges (64 messages) — older pairs drop off the front. Exceeding the cap is logged as a warning, **not** silently dropped without trace.
5. **Model selection via `model_hint` maps.** `OllamaClient` takes `model_map: dict[str, str]` in its constructor, defaulting to `{"sonnet": "sidequest-narrator:latest", "haiku": "sidequest-decomposer:latest", "opus": "sidequest-narrator:latest"}`. The existing callers pass Claude model names (`NARRATOR_MODEL`, `DECOMPOSER_MODEL = "haiku"`) — the Ollama client maps those to local model names. Unknown model keys fail loud with `UnknownModel` error — no silent fallback.
6. **Backend selection via env var.** `SIDEQUEST_LLM_BACKEND` ∈ `{"claude", "ollama"}`. Default `"claude"`. Unknown values raise at factory construction — server fails to start rather than silently running Claude. MLX backend is **not** shipped in Group E; documented as future work.
7. **Ollama base URL via env var.** `SIDEQUEST_OLLAMA_URL` (default `http://localhost:11434`). No auth support — Ollama is local. If unreachable at first call, error is surfaced as `LlmClientError("ollama unreachable")` and the session handler's existing degraded-response path kicks in exactly as it does for Claude timeouts.
8. **Training is offline-only in Group E.** Phase 3 ships a CLI — `uv run sidequest-train --corpus ~/.sidequest/corpus/mined/*.jsonl --base <model> --genre <slug>` — that produces a LoRA adapter on disk. There is **no** runtime LoRA-serving integration in this plan. Deploying an MLX adapter to Ollama requires GGUF conversion which is format-gap work; that is Group F (specialization) or a future plan. Phase 3 deliverable = trained adapter + eval stats + decision log; nothing in `sidequest-server` reads the adapter output.
9. **Base model for fine-tune: Qwen 2.5 7B Instruct.** ADR-073 listed three candidates; pick one and lock it. Rationale: (a) native JSON proficiency matters for DispatchPackage emission, (b) mlx-lm has a well-tested Qwen recipe, (c) 7B fits comfortably on Keith's M-series hardware with room for 16K context + LoRA. Revisiting means amending this plan, not a per-task decision.
10. **Corpus volume gate is non-blocking.** Phase 3 tasks ship regardless of how many rows `~/.sidequest/corpus/` contains. A task in Phase 3 inspects the corpus and prints `{count, min_round, max_round, genres}` — if count is below 500 pairs, the CLI emits a loud `WARNING: training on <N> pairs; ADR-073 recommends 5K+ for base fine-tune. Output adapter is expected to overfit.` Training still runs — this lets Keith smoke the pipeline end-to-end today and kick off real training once Group D gathers enough corpus data from future playtests.

**Non-goals (explicit rejections):**

- **No MLX server-side inference backend.** ADR-073 marks MLX "optional." Deferred: writing an in-daemon MLX inference service + unix-socket RPC is its own plan. Ollama is the local-backend bar for Group E.
- **No Ollama `/api/tools` tool-calling wiring.** The Claude backend doesn't exercise tool-calling in the current code path either. `capabilities().supports_tools` is reported but the `tools: list[ToolDefinition]` request field from ADR-073 §Phase 1 is deferred.
- **No adapter deployment pipeline.** Phase 3 writes `~/.sidequest/loras/<genre>/<base>-<ts>/adapters.safetensors`; nothing reads it at runtime. Don't add Ollama Modelfile generators, don't edit `~/.sidequest/config.yaml`.
- **No GM-panel UI changes.** Backend picker in the UI is Group F concern.
- **No eval dashboard.** Phase 3 training CLI prints `train/val loss` at the end. An A/B eval harness (local vs Claude on identical prompts) is a separate plan.
- **No streaming.** `supports_streaming` is reported as capability but no caller consumes a streaming response in Group E. Narrator is request/response.
- **No prompt-tier auto-downgrade based on `max_context_tokens`.** The orchestrator's existing `select_prompt_tier()` keeps its current inputs. Wiring capabilities into tier selection is a follow-up.
- **No Docker/containerisation.** Ollama install is a Keith-side concern (`brew install ollama` + `ollama pull qwen2.5:7b-instruct`). Plan does not add Dockerfiles, compose files, or install scripts.
- **No migration of existing `ClaudeClientError`, `TimeoutError`, `SubprocessFailed`, `EmptyResponse` error hierarchy.** Ollama gets its own `OllamaClientError` subclass of a new `LlmClientError` base; Claude's existing errors inherit from the same base. No blanket rename.

---

## File Structure

**Phase 1 — server worktree:**

- Modify: `sidequest-server/sidequest/agents/claude_client.py` — rename `ClaudeLike` → `LlmClient`, add `LlmCapabilities` dataclass + `capabilities()` Protocol method + `LlmClientError` base, extend `ClaudeResponse` with `backend: str = "claude-cli"` field, implement `ClaudeClient.capabilities()`.
- Modify: `sidequest-server/sidequest/agents/__init__.py` — export `LlmClient`, `LlmCapabilities`, `LlmClientError`, keep legacy names out (no aliases).
- Modify: `sidequest-server/sidequest/agents/local_dm.py` — swap `ClaudeLike` → `LlmClient` in type hints (5 occurrences).
- Modify: `sidequest-server/sidequest/agents/orchestrator.py` — swap `ClaudeLike` → `LlmClient` (3 occurrences).
- Modify: `sidequest-server/sidequest/server/app.py` — swap `ClaudeLike` → `LlmClient` (3 occurrences).
- Modify: `sidequest-server/sidequest/server/session_handler.py` — swap `ClaudeLike` → `LlmClient` (3 occurrences).
- Modify: `sidequest-server/tests/agents/test_claude_client.py` — swap imports, add test for `capabilities()`.

**Phase 2 — server worktree:**

- Create: `sidequest-server/sidequest/agents/ollama_client.py` — `OllamaClient`, `OllamaClientError`, `UnknownModel`, history-replay logic, HTTP transport DI.
- Create: `sidequest-server/sidequest/agents/llm_factory.py` — `build_llm_client()` reads `SIDEQUEST_LLM_BACKEND`, `SIDEQUEST_OLLAMA_URL`, returns an `LlmClient`.
- Modify: `sidequest-server/sidequest/server/app.py` — replace `claude_client_factory` default `lambda: ClaudeClient()` with `build_llm_client` (factory signature unchanged — still `Callable[[], LlmClient]`).
- Modify: `sidequest-server/sidequest/agents/__init__.py` — export `OllamaClient`, `OllamaClientError`, `build_llm_client`.
- Create: `sidequest-server/tests/agents/test_ollama_client.py` — fake HTTP transport, session history, error paths.
- Create: `sidequest-server/tests/agents/test_llm_factory.py` — env-var handling, unknown backend raises, default is Claude.
- Modify: `sidequest-server/sidequest/telemetry/spans.py` (or wherever agent spans live) — add `backend` span attribute.

**Phase 3 — daemon worktree:**

- Create: `sidequest-daemon/sidequest_daemon/training/__init__.py` — package marker + `TRAINING_SCHEMA_VERSION = 1`.
- Create: `sidequest-daemon/sidequest_daemon/training/corpus_loader.py` — reads Group D `TrainingPair` JSONL, filters degraded rows, yields MLX-LM training examples.
- Create: `sidequest-daemon/sidequest_daemon/training/format.py` — `format_for_qwen(pair: TrainingPair) -> dict` — emits `{"messages": [...]}` in the ChatML format mlx-lm expects.
- Create: `sidequest-daemon/sidequest_daemon/training/trainer.py` — wraps `mlx_lm.lora` programmatic API, handles adapter save path convention, surfaces loss stats.
- Create: `sidequest-daemon/sidequest_daemon/training/cli.py` — `sidequest-train` entrypoint. `--corpus`, `--base`, `--genre`, `--out`, `--iters`, `--batch-size`, `--smoke` flags.
- Modify: `sidequest-daemon/pyproject.toml` — add `mlx-lm>=0.20` under an `[project.optional-dependencies].training` extra; add `[project.scripts]` entry `sidequest-train = "sidequest_daemon.training.cli:main"`.
- Create: `sidequest-daemon/tests/training/__init__.py`.
- Create: `sidequest-daemon/tests/training/test_corpus_loader.py`.
- Create: `sidequest-daemon/tests/training/test_format.py`.
- Create: `sidequest-daemon/tests/training/test_trainer.py` — uses a `FakeTrainer` that records calls; does not run real MLX.
- Create: `sidequest-daemon/tests/training/test_cli.py` — smoke mode only; real training is gated behind `@pytest.mark.slow` and skipped by default.

---

## Phase 1 — LlmClient Abstraction (server worktree)

### Task 1: Create worktree + prove baseline suite is green

**Files:**
- Setup only, no code.

- [ ] **Step 1: Create the worktree**

Run from repo root:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git fetch origin
git worktree add .worktrees/group-e origin/develop -b feat/local-dm-group-e-server
cd .worktrees/group-e
```

Expected: new worktree at `/Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-e`.

- [ ] **Step 2: Confirm the unit suite is green before touching anything**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-e
uv sync
uv run pytest -q
```

Expected: all tests pass. Record the exact count in the commit message for Task 2.

- [ ] **Step 3: Commit the baseline marker**

```bash
git commit --allow-empty -m "chore(group-e): baseline worktree green (N/N tests)"
```

Replace `N/N` with the count from Step 2.

---

### Task 2: Add `LlmClientError` base + `LlmCapabilities` dataclass

**Files:**
- Modify: `sidequest/agents/claude_client.py` (add new classes, reorder imports)
- Modify: `tests/agents/test_claude_client.py` (add capabilities test)

- [ ] **Step 1: Write the failing test**

Append to `tests/agents/test_claude_client.py`:

```python
def test_claude_client_reports_capabilities():
    client = ClaudeClient()
    caps = client.capabilities()
    assert caps.supports_sessions is True
    assert caps.supports_tools is True
    assert caps.supports_streaming is False
    assert caps.max_context_tokens >= 200_000
    assert caps.backend_id == "claude-cli"


def test_llm_capabilities_is_frozen():
    from dataclasses import FrozenInstanceError

    from sidequest.agents.claude_client import LlmCapabilities

    caps = LlmCapabilities(
        backend_id="x",
        supports_sessions=True,
        supports_tools=False,
        max_context_tokens=1,
        supports_streaming=False,
    )
    with pytest.raises(FrozenInstanceError):
        caps.backend_id = "y"  # type: ignore[misc]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_claude_client.py::test_claude_client_reports_capabilities tests/agents/test_claude_client.py::test_llm_capabilities_is_frozen -v
```

Expected: `AttributeError: 'ClaudeClient' object has no attribute 'capabilities'`.

- [ ] **Step 3: Implement `LlmClientError` + `LlmCapabilities`**

Insert in `sidequest/agents/claude_client.py` above the existing error classes:

```python
from dataclasses import dataclass


class LlmClientError(Exception):
    """Base error for any LlmClient backend (Claude CLI, Ollama, future MLX)."""


@dataclass(frozen=True, slots=True)
class LlmCapabilities:
    """Runtime capability report for an LlmClient backend."""

    backend_id: str
    supports_sessions: bool
    supports_tools: bool
    max_context_tokens: int
    supports_streaming: bool
```

Re-base the existing Claude error classes on `LlmClientError`:

```python
class ClaudeClientError(LlmClientError):
    """Base error from Claude CLI subprocess invocations."""
```

(`TimeoutError`, `SubprocessFailed`, `EmptyResponse` already inherit from `ClaudeClientError`, so they transitively become `LlmClientError`.)

- [ ] **Step 4: Implement `ClaudeClient.capabilities()`**

Add inside the `ClaudeClient` class body (after `otel_endpoint` property):

```python
def capabilities(self) -> LlmCapabilities:
    """Report Claude CLI capabilities (ADR-073 Phase 1)."""
    return LlmCapabilities(
        backend_id="claude-cli",
        supports_sessions=True,
        supports_tools=True,
        max_context_tokens=200_000,
        supports_streaming=False,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/agents/test_claude_client.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/claude_client.py tests/agents/test_claude_client.py
git commit -m "feat(llm): add LlmClientError + LlmCapabilities + capabilities() (ADR-073 Phase 1)"
```

---

### Task 3: Extend `ClaudeResponse` with `backend` field

**Files:**
- Modify: `sidequest/agents/claude_client.py`
- Modify: `tests/agents/test_claude_client.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/agents/test_claude_client.py`:

```python
def test_claude_response_carries_backend_tag():
    r = ClaudeResponse(text="hi", input_tokens=1, output_tokens=1, session_id=None)
    assert r.backend == "claude-cli"


def test_claude_response_backend_accepts_override():
    r = ClaudeResponse(text="hi", input_tokens=1, output_tokens=1, session_id=None, backend="ollama")
    assert r.backend == "ollama"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_claude_client.py::test_claude_response_carries_backend_tag -v
```

Expected: `TypeError: __init__() got an unexpected keyword argument 'backend'`.

- [ ] **Step 3: Extend `ClaudeResponse`**

In `sidequest/agents/claude_client.py`, update the class:

```python
class ClaudeResponse:
    """Response from an LlmClient call, including token usage telemetry."""

    __slots__ = ("text", "input_tokens", "output_tokens", "session_id", "backend")

    def __init__(
        self,
        text: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        session_id: str | None = None,
        backend: str = "claude-cli",
    ) -> None:
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.session_id = session_id
        self.backend = backend

    def __repr__(self) -> str:
        return (
            f"ClaudeResponse(text={self.text!r:.40}, "
            f"input_tokens={self.input_tokens}, output_tokens={self.output_tokens}, "
            f"session_id={self.session_id!r}, backend={self.backend!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ClaudeResponse):
            return NotImplemented
        return (
            self.text == other.text
            and self.input_tokens == other.input_tokens
            and self.output_tokens == other.output_tokens
            and self.session_id == other.session_id
            and self.backend == other.backend
        )
```

- [ ] **Step 4: Run full `test_claude_client.py` to catch equality regressions**

```bash
uv run pytest tests/agents/test_claude_client.py -v
```

Expected: all pass. If any existing equality test breaks, it's because the mock constructed a `ClaudeResponse` without setting `backend` on both sides — fix the test by leaving `backend` defaulted on both.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/claude_client.py tests/agents/test_claude_client.py
git commit -m "feat(llm): ClaudeResponse carries backend tag (ADR-073 Phase 1)"
```

---

### Task 4: Rename `ClaudeLike` → `LlmClient` and add `capabilities()` to the Protocol

**Files:**
- Modify: `sidequest/agents/claude_client.py`
- Modify: `sidequest/agents/__init__.py`
- Modify: `sidequest/agents/local_dm.py`
- Modify: `sidequest/agents/orchestrator.py`
- Modify: `sidequest/server/app.py`
- Modify: `sidequest/server/session_handler.py`
- Modify: `tests/agents/test_claude_client.py`

- [ ] **Step 1: Write the failing test**

In `tests/agents/test_claude_client.py`, replace the `ClaudeLike` import and add:

```python
from sidequest.agents.claude_client import LlmClient  # noqa: F401


def test_claude_client_satisfies_llm_client_protocol():
    client = ClaudeClient()
    assert isinstance(client, LlmClient)


def test_llm_client_protocol_requires_capabilities():
    class MissingCaps:
        async def send_with_model(self, prompt: str, model: str) -> ClaudeResponse:
            raise NotImplementedError

        async def send_with_session(self, prompt, model, session_id=None, system_prompt=None,
                                     allowed_tools=None, env_vars=None):
            raise NotImplementedError

    # Missing capabilities() means it does NOT satisfy the Protocol.
    assert not isinstance(MissingCaps(), LlmClient)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_claude_client.py::test_claude_client_satisfies_llm_client_protocol -v
```

Expected: `ImportError: cannot import name 'LlmClient' from 'sidequest.agents.claude_client'`.

- [ ] **Step 3: Rename the Protocol**

In `sidequest/agents/claude_client.py`, change the block at the bottom:

```python
# ---------------------------------------------------------------------------
# LlmClient protocol (ADR-073 Phase 1 — generalised from ClaudeLike)
# ---------------------------------------------------------------------------


@runtime_checkable
class LlmClient(Protocol):
    """Object-safe abstraction over any LLM client backend.

    Production code takes LlmClient so tests can substitute a mock and so
    alternative backends (Ollama, MLX) can slot in via `build_llm_client`.
    Maps to ADR-073 Phase 1 LlmClient trait.
    """

    def capabilities(self) -> LlmCapabilities:
        """Report backend capabilities (ADR-073 Phase 1)."""
        ...

    async def send_with_model(self, prompt: str, model: str) -> ClaudeResponse:
        """Execute a one-shot call with an explicit model."""
        ...

    async def send_with_session(
        self,
        prompt: str,
        model: str,
        session_id: str | None = None,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> ClaudeResponse:
        """Execute a persistent-session call (ADR-066)."""
        ...
```

Delete the old `ClaudeLike` class.

- [ ] **Step 4: Rewrite callers — mechanical rename**

Run this ripgrep + sed pipeline from the worktree root:

```bash
rg -l "ClaudeLike" sidequest tests | xargs sed -i '' 's/ClaudeLike/LlmClient/g'
```

Then open each changed file and sanity-check the docstring lines still read naturally (the pattern appears in `sidequest/agents/local_dm.py` comments and should).

- [ ] **Step 5: Update `sidequest/agents/__init__.py` exports**

Open `sidequest/agents/__init__.py`. Remove `ClaudeLike` from the `__all__` list and the `from ... import` statement. Add:

```python
from sidequest.agents.claude_client import (
    ClaudeClient,
    ClaudeClientBuilder,
    ClaudeClientError,
    ClaudeResponse,
    EmptyResponse,
    LlmCapabilities,
    LlmClient,
    LlmClientError,
    SubprocessFailed,
    TimeoutError,
)

__all__ = [
    "ClaudeClient",
    "ClaudeClientBuilder",
    "ClaudeClientError",
    "ClaudeResponse",
    "EmptyResponse",
    "LlmCapabilities",
    "LlmClient",
    "LlmClientError",
    "SubprocessFailed",
    "TimeoutError",
]
```

- [ ] **Step 6: Run the full suite to shake out missed rename sites**

```bash
uv run pytest -q
```

Expected: all tests pass. If any fail with `NameError: name 'ClaudeLike' is not defined`, rename that site and re-run.

- [ ] **Step 7: Run lint + pyright**

```bash
uv run ruff check sidequest tests
uv run pyright sidequest tests
```

Expected: no new errors. If pyright complains about the `LlmClient` Protocol not being a subtype of `ClaudeLike` in any stored type annotation, that's a leftover; fix by updating the annotation.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor(llm): rename ClaudeLike → LlmClient + Protocol includes capabilities() (ADR-073 Phase 1)"
```

---

### Task 5: Stamp OTEL spans with `backend` attribute

**Files:**
- Modify: `sidequest/telemetry/spans.py` (or the file that defines `agent_call_span` and `agent_call_session_span`)
- Modify: `sidequest/agents/claude_client.py`
- Modify: `tests/agents/test_claude_client.py` (new test on the `ClaudeResponse.backend` surfacing through the span)

- [ ] **Step 1: Locate the agent span helpers**

```bash
grep -n "agent_call_span\|agent_call_session_span" sidequest/telemetry/spans.py
```

Confirm both live there. If they don't, grep the project for the function definition and work from that file.

- [ ] **Step 2: Write the failing test**

Append to `tests/agents/test_claude_client.py`:

```python
def test_claude_client_stamps_backend_on_response(fake_spawn_success):
    # fake_spawn_success is the existing fixture pattern in this file that
    # returns a FakeProcess wrapping a {"result": "...", "usage": {...}} envelope.
    client = ClaudeClient(spawn_fn=fake_spawn_success)
    response = asyncio.run(client.send_with_model("hi", model="sonnet"))
    assert response.backend == "claude-cli"
```

(If `fake_spawn_success` is not the actual fixture name in this file, copy the setup the existing success-path tests use.)

- [ ] **Step 3: Run test to verify baseline (should already pass)**

```bash
uv run pytest tests/agents/test_claude_client.py::test_claude_client_stamps_backend_on_response -v
```

If it fails, the success path in `_run_subprocess` is not setting `backend` on `ClaudeResponse`. Fix: ensure every `ClaudeResponse(...)` constructor call inside `claude_client.py` passes `backend="claude-cli"` explicitly (don't rely on default — makes intent visible).

- [ ] **Step 4: Add `backend` attribute to spans**

In `sidequest/telemetry/spans.py`, for both `agent_call_span` and `agent_call_session_span`, add a `backend` kwarg (default `"claude-cli"`) and set it on the span:

```python
def agent_call_span(*, model: str, prompt_len: int, backend: str = "claude-cli") -> ContextManager[Span]:
    ...
    span.set_attribute("agent.backend", backend)
    ...
```

- [ ] **Step 5: Pass `backend` from `ClaudeClient`**

In `sidequest/agents/claude_client.py`, update the two `with` entries:

```python
with agent_call_span(model=model_label, prompt_len=len(prompt), backend="claude-cli") as span:
...
with agent_call_session_span(model=model, prompt_len=len(prompt), backend="claude-cli") as span:
```

- [ ] **Step 6: Run the suite**

```bash
uv run pytest -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(telemetry): agent spans tagged with backend id (ADR-073 Phase 1)"
```

---

## Phase 2 — Ollama Backend + Factory (server worktree)

### Task 6: Scaffold `OllamaClient` with capabilities + error hierarchy (no HTTP yet)

**Files:**
- Create: `sidequest/agents/ollama_client.py`
- Create: `tests/agents/test_ollama_client.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agents/test_ollama_client.py
"""Tests for OllamaClient — HTTP backend behind LlmClient (ADR-073 Phase 2)."""
from __future__ import annotations

import pytest

from sidequest.agents.claude_client import LlmClient
from sidequest.agents.ollama_client import OllamaClient, OllamaClientError, UnknownModel


def test_ollama_client_satisfies_llm_client_protocol():
    client = OllamaClient(base_url="http://localhost:11434")
    assert isinstance(client, LlmClient)


def test_ollama_client_reports_capabilities():
    client = OllamaClient(base_url="http://localhost:11434")
    caps = client.capabilities()
    assert caps.backend_id == "ollama"
    assert caps.supports_sessions is False
    assert caps.supports_tools is False
    assert caps.max_context_tokens == 16_384
    assert caps.supports_streaming is False


def test_unknown_model_is_ollama_client_error_subclass():
    assert issubclass(UnknownModel, OllamaClientError)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_ollama_client.py -v
```

Expected: `ImportError: No module named 'sidequest.agents.ollama_client'`.

- [ ] **Step 3: Create the minimal module**

```python
# sidequest/agents/ollama_client.py
"""Ollama HTTP backend for LlmClient (ADR-073 Phase 2)."""
from __future__ import annotations

from sidequest.agents.claude_client import (
    ClaudeResponse,
    LlmCapabilities,
    LlmClientError,
)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL_MAP: dict[str, str] = {
    "sonnet": "sidequest-narrator:latest",
    "haiku": "sidequest-decomposer:latest",
    "opus": "sidequest-narrator:latest",
}
OLLAMA_HISTORY_CAP = 32  # exchanges (system + N*2 messages)


class OllamaClientError(LlmClientError):
    """Base error for OllamaClient."""


class UnknownModel(OllamaClientError):
    """Caller asked for a model hint not present in the Ollama model map."""


class OllamaClient:
    """HTTP client against an Ollama server (ADR-073 Phase 2).

    Sessions are simulated client-side: each session_id maps to an in-process
    chat history, replayed on subsequent send_with_session calls.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        model_map: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_map: dict[str, str] = dict(model_map or DEFAULT_MODEL_MAP)
        self._histories: dict[str, list[dict[str, str]]] = {}

    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities(
            backend_id="ollama",
            supports_sessions=False,
            supports_tools=False,
            max_context_tokens=16_384,
            supports_streaming=False,
        )

    async def send_with_model(self, prompt: str, model: str) -> ClaudeResponse:  # noqa: D401
        raise NotImplementedError("wired in Task 7")

    async def send_with_session(
        self,
        prompt: str,
        model: str,
        session_id: str | None = None,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> ClaudeResponse:
        raise NotImplementedError("wired in Task 8")
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run pytest tests/agents/test_ollama_client.py -v
```

Expected: the three scaffolding tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/ollama_client.py tests/agents/test_ollama_client.py
git commit -m "feat(ollama): scaffold OllamaClient + error hierarchy (ADR-073 Phase 2)"
```

---

### Task 7: Implement `OllamaClient.send_with_model` against `/api/generate`

**Files:**
- Modify: `sidequest/agents/ollama_client.py`
- Modify: `tests/agents/test_ollama_client.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/agents/test_ollama_client.py`:

```python
import asyncio
import json

class _FakeHttpResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _ok_generate_body(text: str, eval_count: int = 5, prompt_eval_count: int = 7) -> bytes:
    return json.dumps({
        "model": "sidequest-narrator:latest",
        "response": text,
        "done": True,
        "eval_count": eval_count,
        "prompt_eval_count": prompt_eval_count,
    }).encode()


def test_send_with_model_calls_api_generate_and_maps_tokens():
    calls: list[tuple[str, bytes]] = []

    def fake_http(req):
        calls.append((req.full_url, req.data or b""))
        return _FakeHttpResponse(_ok_generate_body("hello world"))

    client = OllamaClient(http_fn=fake_http)
    response = asyncio.run(client.send_with_model("hi", model="sonnet"))

    assert response.text == "hello world"
    assert response.backend == "ollama"
    assert response.input_tokens == 7
    assert response.output_tokens == 5
    assert response.session_id is None
    assert len(calls) == 1
    url, body_bytes = calls[0]
    assert url == "http://localhost:11434/api/generate"
    body = json.loads(body_bytes)
    assert body["model"] == "sidequest-narrator:latest"
    assert body["prompt"] == "hi"
    assert body["stream"] is False


def test_send_with_model_unknown_hint_raises():
    client = OllamaClient(http_fn=lambda req: pytest.fail("should not call HTTP"))
    with pytest.raises(UnknownModel):
        asyncio.run(client.send_with_model("hi", model="this-model-is-not-mapped"))


def test_send_with_model_non_200_raises_ollama_error():
    def fake_http(req):
        return _FakeHttpResponse(b"server exploded", status=500)

    client = OllamaClient(http_fn=fake_http)
    with pytest.raises(OllamaClientError):
        asyncio.run(client.send_with_model("hi", model="sonnet"))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_ollama_client.py -v
```

Expected: three new tests fail with `NotImplementedError`.

- [ ] **Step 3: Implement `send_with_model` and `http_fn` injection**

Update `sidequest/agents/ollama_client.py`:

```python
from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any
from urllib.request import Request, urlopen

from sidequest.agents.claude_client import (
    ClaudeResponse,
    LlmCapabilities,
    LlmClientError,
)
from sidequest.telemetry.spans import agent_call_span, agent_call_session_span

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL_MAP: dict[str, str] = {
    "sonnet": "sidequest-narrator:latest",
    "haiku": "sidequest-decomposer:latest",
    "opus": "sidequest-narrator:latest",
}
OLLAMA_HISTORY_CAP = 32

HttpFn = Callable[[Request], Any]  # Any because urllib returns a context manager protocol


def _default_http(req: Request) -> Any:
    return urlopen(req, timeout=120)


class OllamaClientError(LlmClientError):
    """Base error for OllamaClient."""


class UnknownModel(OllamaClientError):
    """Caller asked for a model hint not present in the Ollama model map."""


class OllamaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        model_map: dict[str, str] | None = None,
        http_fn: HttpFn | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_map: dict[str, str] = dict(model_map or DEFAULT_MODEL_MAP)
        self._histories: dict[str, list[dict[str, str]]] = {}
        self._http: HttpFn = http_fn or _default_http

    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities(
            backend_id="ollama",
            supports_sessions=False,
            supports_tools=False,
            max_context_tokens=16_384,
            supports_streaming=False,
        )

    def _resolve_model(self, hint: str) -> str:
        resolved = self._model_map.get(hint)
        if resolved is None:
            raise UnknownModel(
                f"model hint {hint!r} not in Ollama model_map keys={sorted(self._model_map.keys())}"
            )
        return resolved

    async def send_with_model(self, prompt: str, model: str) -> ClaudeResponse:
        local_model = self._resolve_model(model)
        with agent_call_span(model=local_model, prompt_len=len(prompt), backend="ollama"):
            body = {"model": local_model, "prompt": prompt, "stream": False}
            return await asyncio.to_thread(self._post_generate, body)

    def _post_generate(self, body: dict[str, object]) -> ClaudeResponse:
        req = Request(
            f"{self._base_url}/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._http(req) as resp:
                status = getattr(resp, "status", 200)
                payload = resp.read()
        except Exception as exc:
            raise OllamaClientError(f"ollama /api/generate transport error: {exc}") from exc
        if status != 200:
            raise OllamaClientError(
                f"ollama /api/generate HTTP {status}: {payload!r:.200}"
            )
        try:
            envelope = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise OllamaClientError(f"ollama /api/generate non-json body: {exc}") from exc
        return ClaudeResponse(
            text=envelope.get("response", ""),
            input_tokens=envelope.get("prompt_eval_count"),
            output_tokens=envelope.get("eval_count"),
            session_id=None,
            backend="ollama",
        )

    async def send_with_session(self, prompt, model, session_id=None, system_prompt=None,
                                 allowed_tools=None, env_vars=None):
        raise NotImplementedError("wired in Task 8")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/agents/test_ollama_client.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/ollama_client.py tests/agents/test_ollama_client.py
git commit -m "feat(ollama): send_with_model hits /api/generate with token mapping"
```

---

### Task 8: Implement `OllamaClient.send_with_session` with client-side history replay

**Files:**
- Modify: `sidequest/agents/ollama_client.py`
- Modify: `tests/agents/test_ollama_client.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/agents/test_ollama_client.py`:

```python
def _ok_chat_body(text: str, eval_count: int = 5, prompt_eval_count: int = 7) -> bytes:
    return json.dumps({
        "model": "sidequest-narrator:latest",
        "message": {"role": "assistant", "content": text},
        "done": True,
        "eval_count": eval_count,
        "prompt_eval_count": prompt_eval_count,
    }).encode()


def test_send_with_session_establishes_new_session():
    calls: list[dict] = []

    def fake_http(req):
        body = json.loads(req.data)
        calls.append(body)
        return _FakeHttpResponse(_ok_chat_body("hi back"))

    client = OllamaClient(http_fn=fake_http)
    response = asyncio.run(client.send_with_session(
        prompt="hello",
        model="sonnet",
        session_id=None,
        system_prompt="you are a bot",
    ))

    assert response.text == "hi back"
    assert response.backend == "ollama"
    assert response.session_id is not None  # fresh uuid
    assert len(calls) == 1
    call = calls[0]
    assert call["messages"] == [
        {"role": "system", "content": "you are a bot"},
        {"role": "user", "content": "hello"},
    ]
    assert call["stream"] is False


def test_send_with_session_resume_replays_history():
    bodies = [
        _ok_chat_body("turn 1 reply"),
        _ok_chat_body("turn 2 reply"),
    ]
    calls: list[dict] = []

    def fake_http(req):
        calls.append(json.loads(req.data))
        return _FakeHttpResponse(bodies.pop(0))

    client = OllamaClient(http_fn=fake_http)
    first = asyncio.run(client.send_with_session(
        prompt="turn 1",
        model="sonnet",
        session_id=None,
        system_prompt="sys",
    ))
    sid = first.session_id
    asyncio.run(client.send_with_session(
        prompt="turn 2",
        model="sonnet",
        session_id=sid,
    ))

    # Second call must replay the full history (system, u1, a1, u2).
    assert calls[1]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "turn 1"},
        {"role": "assistant", "content": "turn 1 reply"},
        {"role": "user", "content": "turn 2"},
    ]


def test_send_with_session_unknown_session_id_raises():
    client = OllamaClient(http_fn=lambda req: pytest.fail("no http expected"))
    with pytest.raises(OllamaClientError):
        asyncio.run(client.send_with_session(
            prompt="hi",
            model="sonnet",
            session_id="00000000-0000-0000-0000-000000000000",
        ))


def test_send_with_session_history_cap_drops_oldest_pairs(caplog):
    # Drive the client past OLLAMA_HISTORY_CAP and assert it drops oldest
    # exchanges while preserving the leading system message.
    from sidequest.agents.ollama_client import OLLAMA_HISTORY_CAP
    reply_bodies = [_ok_chat_body(f"reply {i}") for i in range(OLLAMA_HISTORY_CAP + 2)]

    def fake_http(req):
        return _FakeHttpResponse(reply_bodies.pop(0))

    client = OllamaClient(http_fn=fake_http)
    first = asyncio.run(client.send_with_session(
        prompt="turn 0",
        model="sonnet",
        session_id=None,
        system_prompt="sys",
    ))
    sid = first.session_id
    with caplog.at_level("WARNING"):
        for i in range(1, OLLAMA_HISTORY_CAP + 2):
            asyncio.run(client.send_with_session(
                prompt=f"turn {i}",
                model="sonnet",
                session_id=sid,
            ))

    history = client._histories[sid]
    # System is always first, and user+assistant pairs fit within the cap.
    assert history[0]["role"] == "system"
    assert len(history) <= OLLAMA_HISTORY_CAP * 2 + 1
    assert any("history_cap_exceeded" in rec.message for rec in caplog.records)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_ollama_client.py -v
```

Expected: new tests fail with `NotImplementedError`.

- [ ] **Step 3: Implement session replay**

Replace the stub `send_with_session` in `ollama_client.py`:

```python
import logging
import uuid

logger = logging.getLogger(__name__)

# ... inside OllamaClient class:

async def send_with_session(
    self,
    prompt: str,
    model: str,
    session_id: str | None = None,
    system_prompt: str | None = None,
    allowed_tools: list[str] | None = None,  # noqa: ARG002 — ollama ignores tools
    env_vars: dict[str, str] | None = None,  # noqa: ARG002 — ollama ignores env vars
) -> ClaudeResponse:
    local_model = self._resolve_model(model)

    if session_id is None:
        new_id = str(uuid.uuid4())
        history: list[dict[str, str]] = []
        if system_prompt:
            history.append({"role": "system", "content": system_prompt})
        history.append({"role": "user", "content": prompt})
        self._histories[new_id] = history
        session_to_return = new_id
    else:
        history = self._histories.get(session_id)
        if history is None:
            raise OllamaClientError(
                f"ollama session_id {session_id!r} is not known to this client "
                f"(process restart clears session state)"
            )
        history.append({"role": "user", "content": prompt})
        session_to_return = session_id

    # Enforce cap: keep the leading system message plus the most recent
    # (cap * 2) user+assistant messages.
    self._cap_history(self._histories[session_to_return])

    with agent_call_session_span(model=local_model, prompt_len=len(prompt), backend="ollama"):
        body = {
            "model": local_model,
            "messages": list(self._histories[session_to_return]),
            "stream": False,
        }
        response = await asyncio.to_thread(self._post_chat, body)

    # Append assistant reply to history for next turn.
    self._histories[session_to_return].append(
        {"role": "assistant", "content": response.text}
    )
    self._cap_history(self._histories[session_to_return])

    return ClaudeResponse(
        text=response.text,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        session_id=session_to_return,
        backend="ollama",
    )


def _cap_history(self, history: list[dict[str, str]]) -> None:
    """Keep leading system message + most recent exchanges up to cap."""
    max_total = OLLAMA_HISTORY_CAP * 2 + (1 if history and history[0]["role"] == "system" else 0)
    if len(history) <= max_total:
        return
    logger.warning("ollama.history_cap_exceeded len=%d cap=%d", len(history), max_total)
    if history and history[0]["role"] == "system":
        system = history[0]
        tail = history[-(OLLAMA_HISTORY_CAP * 2):]
        history[:] = [system, *tail]
    else:
        history[:] = history[-(OLLAMA_HISTORY_CAP * 2):]


def _post_chat(self, body: dict[str, object]) -> ClaudeResponse:
    req = Request(
        f"{self._base_url}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with self._http(req) as resp:
            status = getattr(resp, "status", 200)
            payload = resp.read()
    except Exception as exc:
        raise OllamaClientError(f"ollama /api/chat transport error: {exc}") from exc
    if status != 200:
        raise OllamaClientError(f"ollama /api/chat HTTP {status}: {payload!r:.200}")
    try:
        envelope = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise OllamaClientError(f"ollama /api/chat non-json body: {exc}") from exc
    message = envelope.get("message") or {}
    return ClaudeResponse(
        text=message.get("content", ""),
        input_tokens=envelope.get("prompt_eval_count"),
        output_tokens=envelope.get("eval_count"),
        session_id=None,  # filled in by caller
        backend="ollama",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/agents/test_ollama_client.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/ollama_client.py tests/agents/test_ollama_client.py
git commit -m "feat(ollama): send_with_session with client-side history replay + cap"
```

---

### Task 9: Build `llm_factory.build_llm_client` + env-var selection

**Files:**
- Create: `sidequest/agents/llm_factory.py`
- Create: `tests/agents/test_llm_factory.py`
- Modify: `sidequest/agents/__init__.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agents/test_llm_factory.py
"""Tests for llm_factory.build_llm_client — env-var backend selection."""
from __future__ import annotations

import pytest

from sidequest.agents.claude_client import ClaudeClient, LlmClient
from sidequest.agents.llm_factory import UnknownBackend, build_llm_client
from sidequest.agents.ollama_client import OllamaClient


def test_default_is_claude(monkeypatch):
    monkeypatch.delenv("SIDEQUEST_LLM_BACKEND", raising=False)
    client = build_llm_client()
    assert isinstance(client, ClaudeClient)
    assert isinstance(client, LlmClient)


def test_explicit_claude(monkeypatch):
    monkeypatch.setenv("SIDEQUEST_LLM_BACKEND", "claude")
    client = build_llm_client()
    assert isinstance(client, ClaudeClient)


def test_ollama_backend_picks_url_from_env(monkeypatch):
    monkeypatch.setenv("SIDEQUEST_LLM_BACKEND", "ollama")
    monkeypatch.setenv("SIDEQUEST_OLLAMA_URL", "http://example.local:9000")
    client = build_llm_client()
    assert isinstance(client, OllamaClient)
    assert client._base_url == "http://example.local:9000"


def test_unknown_backend_raises(monkeypatch):
    monkeypatch.setenv("SIDEQUEST_LLM_BACKEND", "gpt4")
    with pytest.raises(UnknownBackend):
        build_llm_client()


def test_whitespace_and_case_insensitivity(monkeypatch):
    monkeypatch.setenv("SIDEQUEST_LLM_BACKEND", " CLAUDE  ")
    assert isinstance(build_llm_client(), ClaudeClient)
    monkeypatch.setenv("SIDEQUEST_LLM_BACKEND", "Ollama")
    assert isinstance(build_llm_client(), OllamaClient)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_llm_factory.py -v
```

Expected: `ImportError: No module named 'sidequest.agents.llm_factory'`.

- [ ] **Step 3: Implement the factory**

```python
# sidequest/agents/llm_factory.py
"""LlmClient factory — selects backend from env (ADR-073 Phase 1/2)."""
from __future__ import annotations

import os

from sidequest.agents.claude_client import ClaudeClient, LlmClient, LlmClientError
from sidequest.agents.ollama_client import DEFAULT_OLLAMA_URL, OllamaClient

ENV_BACKEND = "SIDEQUEST_LLM_BACKEND"
ENV_OLLAMA_URL = "SIDEQUEST_OLLAMA_URL"

_VALID_BACKENDS = frozenset({"claude", "ollama"})


class UnknownBackend(LlmClientError):
    """SIDEQUEST_LLM_BACKEND value was not one of the supported backends."""


def build_llm_client() -> LlmClient:
    """Return the configured LlmClient. Default: ClaudeClient.

    Fails loudly for unknown backend values — no silent fallback (CLAUDE.md).
    """
    raw = os.environ.get(ENV_BACKEND, "claude")
    key = raw.strip().lower()
    if key not in _VALID_BACKENDS:
        raise UnknownBackend(
            f"{ENV_BACKEND}={raw!r} not supported; pick one of {sorted(_VALID_BACKENDS)}"
        )
    if key == "claude":
        return ClaudeClient()
    if key == "ollama":
        base_url = os.environ.get(ENV_OLLAMA_URL, DEFAULT_OLLAMA_URL)
        return OllamaClient(base_url=base_url)
    # Unreachable — the set check above covers all known backends.
    raise UnknownBackend(f"backend {key!r} recognised but not wired")
```

- [ ] **Step 4: Add exports to `sidequest/agents/__init__.py`**

```python
from sidequest.agents.llm_factory import UnknownBackend, build_llm_client
from sidequest.agents.ollama_client import OllamaClient, OllamaClientError

# extend __all__:
__all__ += [
    "OllamaClient",
    "OllamaClientError",
    "UnknownBackend",
    "build_llm_client",
]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/agents/test_llm_factory.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/llm_factory.py sidequest/agents/__init__.py tests/agents/test_llm_factory.py
git commit -m "feat(llm): backend factory reads SIDEQUEST_LLM_BACKEND env (ADR-073 Phase 2)"
```

---

### Task 10: Wire factory into `server/app.py` so Ollama is reachable end-to-end

**Files:**
- Modify: `sidequest/server/app.py`
- Modify: `tests/server/test_app.py` (or the equivalent) — add a test that confirms the factory is used by default

- [ ] **Step 1: Write the failing test**

Append (or create) in `tests/server/test_app.py`:

```python
from sidequest.server.app import create_app


def test_create_app_uses_build_llm_client_by_default(monkeypatch):
    monkeypatch.delenv("SIDEQUEST_LLM_BACKEND", raising=False)
    app = create_app()
    # The session-handler factory should return a ClaudeClient instance.
    from sidequest.agents.claude_client import ClaudeClient
    client = app.state.session_handler._client_factory()
    assert isinstance(client, ClaudeClient)


def test_create_app_honours_ollama_env(monkeypatch):
    monkeypatch.setenv("SIDEQUEST_LLM_BACKEND", "ollama")
    app = create_app()
    from sidequest.agents.ollama_client import OllamaClient
    client = app.state.session_handler._client_factory()
    assert isinstance(client, OllamaClient)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/server/test_app.py::test_create_app_uses_build_llm_client_by_default tests/server/test_app.py::test_create_app_honours_ollama_env -v
```

Expected: either `claude_client_factory` defaults to `lambda: ClaudeClient()` (test 2 fails because the env var is ignored) or the attribute path is wrong (fix the test first if so).

- [ ] **Step 3: Swap the default factory**

In `sidequest/server/app.py`, find the resolution of `claude_client_factory`:

```python
# old:
resolved_client_factory: Callable[[], LlmClient] = (
    claude_client_factory if claude_client_factory is not None else lambda: ClaudeClient()
)

# new:
from sidequest.agents.llm_factory import build_llm_client

resolved_client_factory: Callable[[], LlmClient] = (
    claude_client_factory if claude_client_factory is not None else build_llm_client
)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/server/test_app.py -v
```

Expected: both new tests pass, no regressions elsewhere.

- [ ] **Step 5: Run the full server suite**

```bash
uv run pytest -q
```

Expected: all pass. If anything failed because an old test asserted `isinstance(..., ClaudeClient)` in a place where it should now be `isinstance(..., LlmClient)`, relax the assertion.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(server): default factory uses build_llm_client so SIDEQUEST_LLM_BACKEND=ollama works (ADR-073 Phase 2)"
```

---

### Task 11: Document the configuration surface

**Files:**
- Modify: `README.md` (of sidequest-server, if one exists; otherwise orchestrator root)
- Create: `docs/llm-backends.md` (orchestrator root, reachable by Keith from CLAUDE.md)
- Modify: `CLAUDE.md` (orchestrator) — add a one-line pointer under "ADR Index" → Narrator/text category.

- [ ] **Step 1: Write the docs page**

```markdown
# LLM Backend Configuration (ADR-073 Phase 1/2)

The server selects its LLM backend at startup via two environment variables.

## Variables

| Variable | Values | Default |
|----------|--------|---------|
| `SIDEQUEST_LLM_BACKEND` | `claude` \| `ollama` | `claude` |
| `SIDEQUEST_OLLAMA_URL` | Any URL | `http://localhost:11434` |

`SIDEQUEST_LLM_BACKEND=claude` uses the Claude CLI subprocess (ADR-001).
`SIDEQUEST_LLM_BACKEND=ollama` hits an Ollama server.

Unknown values fail loud at server start (`UnknownBackend`). No silent fallback.

## Ollama install (macOS)

```
brew install ollama
ollama serve &
ollama pull qwen2.5:7b-instruct
ollama create sidequest-narrator -f Modelfile-narrator  # optional alias
```

Until Group E Phase 3 trains real adapters, `sidequest-narrator:latest` points at
the base Qwen model — narration quality will be noticeably below Claude.

## Capabilities

Each backend advertises its capabilities via `LlmClient.capabilities()`. See
`sidequest/agents/claude_client.py::LlmCapabilities`. The orchestrator does not
currently act on these values — prompt-tier selection ignores them — but
telemetry is tagged with `agent.backend` so the GM panel can tell which backend
served a given turn.

## Testing Ollama without real Ollama

`OllamaClient(http_fn=...)` lets tests inject a fake HTTP transport. See
`tests/agents/test_ollama_client.py` for the canonical `_FakeHttpResponse`
fixture.
```

Save to `/Users/slabgorb/Projects/oq-1/docs/llm-backends.md`.

- [ ] **Step 2: Point CLAUDE.md at the new doc**

In `CLAUDE.md`, under the "Narrator / text" ADR-073 entry, append a parenthetical:

```markdown
- 073 Local Fine-Tuned Model Architecture — Accepted · config surface: `docs/llm-backends.md`
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/llm-backends.md
git commit -m "docs(llm): document SIDEQUEST_LLM_BACKEND config surface"
```

---

### Task 12: Server-side `just check` green + open PR

**Files:** none — validation gate.

- [ ] **Step 1: Run the full gate**

```bash
cd /Users/slabgorb/Projects/oq-1
just server-check
```

Expected: lint clean, all tests pass.

- [ ] **Step 2: Push and open PR**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-e
git push -u origin feat/local-dm-group-e-server
gh pr create --base develop --title "feat: local DM group E (server) — LlmClient abstraction + Ollama backend" --body "$(cat <<'EOF'
## Summary

Ships ADR-073 Phase 1 + Phase 2 on the server side.

- Renamed `ClaudeLike` → `LlmClient`; added `LlmCapabilities` + `LlmClientError` base.
- Added `backend` field to `ClaudeResponse` for OTEL tagging.
- New `OllamaClient` hits `/api/generate` + `/api/chat` with client-side session history replay.
- New `build_llm_client()` factory honours `SIDEQUEST_LLM_BACKEND` env var; default is `claude`.
- Docs: `docs/llm-backends.md`.

Training pipeline (Phase 3) lands in a separate daemon-side PR.

## Test plan
- [x] `uv run pytest` green in worktree
- [ ] Smoke: `SIDEQUEST_LLM_BACKEND=ollama SIDEQUEST_OLLAMA_URL=http://localhost:11434 just server` + one turn
EOF
)"
```

---

## Phase 3 — MLX-LM Training Pipeline (daemon worktree)

### Task 13: Daemon worktree + optional-dep scaffold

**Files:**
- Modify: `sidequest-daemon/pyproject.toml`

- [ ] **Step 1: Create the daemon worktree**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
git fetch origin
git worktree add .worktrees/group-e origin/develop -b feat/local-dm-group-e-daemon
cd .worktrees/group-e
uv sync
uv run pytest -q
```

Expected: green baseline. Record count for the PR body.

- [ ] **Step 2: Add the `training` optional-dep group + console script**

Edit `sidequest-daemon/pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=0.23",
    "opentelemetry-api>=1.20",
    "opentelemetry-sdk>=1.20",
]
training = [
    "mlx-lm>=0.20",
]

[project.scripts]
sidequest-renderer = "sidequest_daemon.media.daemon:main"
sidequest-train = "sidequest_daemon.training.cli:main"
```

- [ ] **Step 3: Install the training extra**

```bash
uv sync --extra training
```

Expected: `mlx-lm` resolves. If it fails on Linux CI, the extra is correctly optional — training is macOS-only.

- [ ] **Step 4: Commit**

```bash
git add sidequest-daemon/pyproject.toml sidequest-daemon/uv.lock
git commit -m "chore(daemon): add training optional-dep group + sidequest-train console script"
```

---

### Task 14: `corpus_loader` — read Group D JSONL into typed rows

**Files:**
- Create: `sidequest_daemon/training/__init__.py`
- Create: `sidequest_daemon/training/corpus_loader.py`
- Create: `tests/training/__init__.py`
- Create: `tests/training/test_corpus_loader.py`
- Create: `tests/training/fixtures/mined_sample.jsonl`

- [ ] **Step 1: Write the failing test**

```python
# tests/training/test_corpus_loader.py
"""Tests for corpus_loader — reading Group D mined JSONL."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sidequest_daemon.training.corpus_loader import (
    CorpusStats,
    load_training_pairs,
    summarise,
)


FIXTURE = Path(__file__).parent / "fixtures" / "mined_sample.jsonl"


def test_load_training_pairs_yields_all_rows():
    pairs = list(load_training_pairs([FIXTURE]))
    assert len(pairs) == 3
    assert {p.genre for p in pairs} == {"caverns_and_claudes", "heavy_metal"}


def test_load_training_pairs_skips_malformed(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json\n" + FIXTURE.read_text())
    pairs = list(load_training_pairs([bad]))
    # First line skipped, remaining 3 loaded.
    assert len(pairs) == 3


def test_load_training_pairs_skips_empty_text(tmp_path):
    bad = tmp_path / "empty.jsonl"
    row = json.loads(FIXTURE.read_text().splitlines()[0])
    row["input_text"] = ""
    bad.write_text(json.dumps(row) + "\n")
    pairs = list(load_training_pairs([bad]))
    assert pairs == []


def test_summarise_counts_by_genre():
    stats = summarise(load_training_pairs([FIXTURE]))
    assert isinstance(stats, CorpusStats)
    assert stats.total == 3
    assert stats.by_genre == {"caverns_and_claudes": 2, "heavy_metal": 1}
    assert stats.min_round <= stats.max_round
```

- [ ] **Step 2: Write the JSONL fixture**

```
# tests/training/fixtures/mined_sample.jsonl
{"schema_version": 1, "genre": "caverns_and_claudes", "world": "forge", "round_number": 0, "input_text": "PC says hello", "output_text": "The tavern door creaks.", "provenance": {"source_save": "/tmp/a.db", "event_seq": 10}}
{"schema_version": 1, "genre": "caverns_and_claudes", "world": "forge", "round_number": 1, "input_text": "PC orders ale", "output_text": "The barkeep nods.", "provenance": {"source_save": "/tmp/a.db", "event_seq": 12}}
{"schema_version": 1, "genre": "heavy_metal", "world": "necropolis", "round_number": 3, "input_text": "PC starts a fight", "output_text": "Chairs fly. Glass shatters.", "provenance": {"source_save": "/tmp/b.db", "event_seq": 44}}
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/training/test_corpus_loader.py -v
```

Expected: `ImportError: No module named 'sidequest_daemon.training'`.

- [ ] **Step 4: Implement the loader**

```python
# sidequest_daemon/training/__init__.py
TRAINING_SCHEMA_VERSION = 1

__all__ = ["TRAINING_SCHEMA_VERSION"]
```

```python
# sidequest_daemon/training/corpus_loader.py
"""Read Group D `TrainingPair` JSONL into typed rows (ADR-073 Phase 3)."""
from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


class MineProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_save: str
    event_seq: int | None


class TrainingPair(BaseModel):
    """Locally-mirrored TrainingPair schema from sidequest-server/sidequest/corpus.

    We keep a copy instead of importing to avoid a daemon → server dep.
    """

    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    genre: str
    world: str
    round_number: int = Field(ge=0)
    input_text: str = Field(min_length=1)
    output_text: str = Field(min_length=1)
    provenance: MineProvenance


@dataclass(frozen=True)
class CorpusStats:
    total: int
    by_genre: dict[str, int]
    min_round: int
    max_round: int


def load_training_pairs(paths: Iterable[Path]) -> Iterator[TrainingPair]:
    """Yield TrainingPair rows from JSONL files; skip-and-log malformed lines."""
    for path in paths:
        with Path(path).open() as fh:
            for idx, raw in enumerate(fh, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj: Any = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning("corpus.bad_json path=%s line=%d err=%s", path, idx, exc)
                    continue
                try:
                    yield TrainingPair.model_validate(obj)
                except ValidationError as exc:
                    logger.warning("corpus.bad_schema path=%s line=%d err=%s", path, idx, exc)


def summarise(pairs: Iterable[TrainingPair]) -> CorpusStats:
    pairs = list(pairs)
    if not pairs:
        return CorpusStats(total=0, by_genre={}, min_round=0, max_round=0)
    by_genre = Counter(p.genre for p in pairs)
    rounds = [p.round_number for p in pairs]
    return CorpusStats(
        total=len(pairs),
        by_genre=dict(by_genre),
        min_round=min(rounds),
        max_round=max(rounds),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/training/test_corpus_loader.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest_daemon/training/__init__.py sidequest_daemon/training/corpus_loader.py tests/training/
git commit -m "feat(training): corpus_loader reads Group D mined JSONL (ADR-073 Phase 3)"
```

---

### Task 15: `format.format_for_qwen` — emit ChatML messages shape

**Files:**
- Create: `sidequest_daemon/training/format.py`
- Create: `tests/training/test_format.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/training/test_format.py
"""Tests for training format — ChatML for Qwen 2.5."""
from __future__ import annotations

from sidequest_daemon.training.corpus_loader import MineProvenance, TrainingPair
from sidequest_daemon.training.format import (
    QWEN_SYSTEM_PROMPT,
    format_for_qwen,
)


def _pair(input_text="in", output_text="out") -> TrainingPair:
    return TrainingPair(
        schema_version=1,
        genre="caverns_and_claudes",
        world="forge",
        round_number=0,
        input_text=input_text,
        output_text=output_text,
        provenance=MineProvenance(source_save="/tmp/s.db", event_seq=1),
    )


def test_format_for_qwen_emits_messages():
    out = format_for_qwen(_pair())
    assert out == {
        "messages": [
            {"role": "system", "content": QWEN_SYSTEM_PROMPT},
            {"role": "user", "content": "in"},
            {"role": "assistant", "content": "out"},
        ]
    }


def test_format_includes_genre_tag_when_asked():
    out = format_for_qwen(_pair(), include_genre_tag=True)
    # Genre is prepended to the system prompt.
    assert out["messages"][0]["content"].startswith("[genre=caverns_and_claudes]")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/training/test_format.py -v
```

Expected: `ImportError: No module named 'sidequest_daemon.training.format'`.

- [ ] **Step 3: Implement the formatter**

```python
# sidequest_daemon/training/format.py
"""Emit ChatML training examples for Qwen 2.5 mlx-lm fine-tune (ADR-073 Phase 3)."""
from __future__ import annotations

from sidequest_daemon.training.corpus_loader import TrainingPair

QWEN_SYSTEM_PROMPT = (
    "You are the SideQuest narrator. Respond with in-world prose grounded in "
    "game state. Obey genre truth. Never narrate for the player."
)


def format_for_qwen(pair: TrainingPair, *, include_genre_tag: bool = False) -> dict:
    system = QWEN_SYSTEM_PROMPT
    if include_genre_tag:
        system = f"[genre={pair.genre}] {system}"
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": pair.input_text},
            {"role": "assistant", "content": pair.output_text},
        ]
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/training/test_format.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/training/format.py tests/training/test_format.py
git commit -m "feat(training): Qwen ChatML formatter for TrainingPair rows"
```

---

### Task 16: `trainer.Trainer` — thin wrapper over mlx-lm's programmatic API

**Files:**
- Create: `sidequest_daemon/training/trainer.py`
- Create: `tests/training/test_trainer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/training/test_trainer.py
"""Tests for trainer.py — uses a FakeTrainer, does NOT run real MLX."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest_daemon.training.corpus_loader import MineProvenance, TrainingPair
from sidequest_daemon.training.trainer import TrainerConfig, run_training


def _pair(i: int = 0) -> TrainingPair:
    return TrainingPair(
        schema_version=1,
        genre="g",
        world="w",
        round_number=i,
        input_text=f"in {i}",
        output_text=f"out {i}",
        provenance=MineProvenance(source_save="/tmp/s.db", event_seq=i),
    )


def test_run_training_invokes_trainer_and_writes_adapter(tmp_path):
    calls: list[dict] = []

    def fake_trainer(**kwargs) -> dict:
        calls.append(kwargs)
        adapter_path = Path(kwargs["adapter_path"])
        adapter_path.mkdir(parents=True, exist_ok=True)
        (adapter_path / "adapters.safetensors").write_bytes(b"\x00" * 8)
        return {"final_train_loss": 1.23, "final_val_loss": 1.45, "iters": kwargs["iters"]}

    cfg = TrainerConfig(
        pairs=[_pair(i) for i in range(4)],
        base_model="Qwen/Qwen2.5-7B-Instruct",
        out_dir=tmp_path / "loras" / "g",
        iters=3,
        batch_size=2,
    )
    result = run_training(cfg, trainer_fn=fake_trainer)

    assert (result.adapter_path / "adapters.safetensors").is_file()
    assert result.stats["iters"] == 3
    assert len(calls) == 1


def test_run_training_empty_pairs_raises():
    cfg = TrainerConfig(pairs=[], base_model="x", out_dir=Path("/tmp/unused"), iters=1, batch_size=1)
    with pytest.raises(ValueError):
        run_training(cfg, trainer_fn=lambda **_: {"iters": 0})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/training/test_trainer.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement the trainer**

```python
# sidequest_daemon/training/trainer.py
"""Thin wrapper over mlx-lm fine-tune, used by sidequest-train CLI (ADR-073 Phase 3).

The mlx-lm invocation is dependency-injected via `trainer_fn` so tests can
exercise the surrounding plumbing without spinning GPU work.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sidequest_daemon.training.corpus_loader import TrainingPair
from sidequest_daemon.training.format import format_for_qwen


TrainerFn = Callable[..., dict]


@dataclass
class TrainerConfig:
    pairs: list[TrainingPair]
    base_model: str
    out_dir: Path
    iters: int
    batch_size: int
    genre: str | None = None
    include_genre_tag: bool = False
    seed: int = 0
    extra: dict = field(default_factory=dict)


@dataclass
class TrainingResult:
    adapter_path: Path
    stats: dict


def _default_trainer(**kwargs) -> dict:
    # Lazy import — mlx-lm is an optional extra, not imported at daemon boot.
    from mlx_lm.lora import run as mlx_lora_run  # type: ignore[import-not-found]

    return mlx_lora_run(**kwargs)


def run_training(cfg: TrainerConfig, *, trainer_fn: TrainerFn | None = None) -> TrainingResult:
    if not cfg.pairs:
        raise ValueError("run_training called with empty pairs list")

    ts = time.strftime("%Y%m%d-%H%M%S")
    model_slug = cfg.base_model.split("/")[-1]
    adapter_path = cfg.out_dir / f"{model_slug}-{ts}"
    adapter_path.mkdir(parents=True, exist_ok=True)

    # Write the ChatML JSONL that mlx-lm reads.
    train_jsonl = adapter_path / "train.jsonl"
    with train_jsonl.open("w") as fh:
        for pair in cfg.pairs:
            fh.write(json.dumps(format_for_qwen(pair, include_genre_tag=cfg.include_genre_tag)))
            fh.write("\n")

    fn = trainer_fn or _default_trainer
    stats = fn(
        model=cfg.base_model,
        data=str(train_jsonl.parent),
        adapter_path=str(adapter_path),
        iters=cfg.iters,
        batch_size=cfg.batch_size,
        seed=cfg.seed,
        **cfg.extra,
    )
    return TrainingResult(adapter_path=adapter_path, stats=stats)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/training/test_trainer.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/training/trainer.py tests/training/test_trainer.py
git commit -m "feat(training): trainer wrapper over mlx-lm lora with DI"
```

---

### Task 17: `cli.main` — `sidequest-train` entrypoint

**Files:**
- Create: `sidequest_daemon/training/cli.py`
- Create: `tests/training/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/training/test_cli.py
"""Tests for sidequest-train CLI — exercised in --smoke mode only."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sidequest_daemon.training.cli import main


FIXTURE = Path(__file__).parent / "fixtures" / "mined_sample.jsonl"


def test_cli_smoke_uses_fake_trainer(tmp_path, monkeypatch, capsys):
    out = tmp_path / "loras"
    rc = main([
        "--corpus", str(FIXTURE),
        "--base", "Qwen/Qwen2.5-7B-Instruct",
        "--out", str(out),
        "--iters", "1",
        "--batch-size", "1",
        "--smoke",
    ])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "total=3" in captured
    assert "caverns_and_claudes" in captured
    # Smoke mode writes a dummy adapter.
    adapters = list(out.rglob("adapters.safetensors"))
    assert len(adapters) == 1


def test_cli_low_volume_warning(tmp_path, capsys):
    tiny = tmp_path / "tiny.jsonl"
    row = json.loads(FIXTURE.read_text().splitlines()[0])
    tiny.write_text(json.dumps(row) + "\n")
    rc = main([
        "--corpus", str(tiny),
        "--base", "Qwen/Qwen2.5-7B-Instruct",
        "--out", str(tmp_path / "loras"),
        "--iters", "1",
        "--batch-size", "1",
        "--smoke",
    ])
    assert rc == 0
    err = capsys.readouterr().err
    assert "ADR-073 recommends 5K+" in err


def test_cli_empty_corpus_nonzero_exit(tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    rc = main([
        "--corpus", str(empty),
        "--base", "Qwen/Qwen2.5-7B-Instruct",
        "--out", str(tmp_path / "loras"),
        "--iters", "1",
        "--batch-size", "1",
        "--smoke",
    ])
    assert rc == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/training/test_cli.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement the CLI**

```python
# sidequest_daemon/training/cli.py
"""`sidequest-train` CLI — train a genre LoRA adapter (ADR-073 Phase 3)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sidequest_daemon.training.corpus_loader import (
    CorpusStats,
    load_training_pairs,
    summarise,
)
from sidequest_daemon.training.trainer import (
    TrainerConfig,
    TrainingResult,
    run_training,
)

LOW_VOLUME_THRESHOLD = 500


def _fake_smoke_trainer(**kwargs) -> dict:
    """Smoke-mode stand-in: writes a dummy adapter + returns fake stats."""
    adapter_path = Path(kwargs["adapter_path"])
    adapter_path.mkdir(parents=True, exist_ok=True)
    (adapter_path / "adapters.safetensors").write_bytes(b"\x00" * 32)
    return {
        "final_train_loss": None,
        "final_val_loss": None,
        "iters": kwargs.get("iters", 0),
        "mode": "smoke",
    }


def _parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="sidequest-train")
    p.add_argument("--corpus", nargs="+", required=True, type=Path,
                   help="Group D mined JSONL file(s).")
    p.add_argument("--base", required=True, help="Base HF model id (e.g. Qwen/Qwen2.5-7B-Instruct).")
    p.add_argument("--out", required=True, type=Path, help="Output directory for adapters.")
    p.add_argument("--iters", type=int, required=True)
    p.add_argument("--batch-size", type=int, required=True)
    p.add_argument("--genre", default=None, help="Filter corpus to this genre slug.")
    p.add_argument("--include-genre-tag", action="store_true",
                   help="Prepend [genre=X] to system prompt in training data.")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--smoke", action="store_true",
                   help="Use a fake trainer that writes a dummy adapter. No GPU work.")
    return p.parse_args(argv)


def _print_stats(stats: CorpusStats) -> None:
    print(f"corpus: total={stats.total} min_round={stats.min_round} max_round={stats.max_round}")
    for genre, n in sorted(stats.by_genre.items()):
        print(f"  {genre}: {n}")


def _warn_low_volume(stats: CorpusStats) -> None:
    if 0 < stats.total < LOW_VOLUME_THRESHOLD:
        print(
            f"WARNING: training on {stats.total} pairs; "
            f"ADR-073 recommends 5K+ for base fine-tune. "
            f"Output adapter is expected to overfit.",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv if argv is not None else sys.argv[1:])
    pairs = list(load_training_pairs(args.corpus))
    if args.genre is not None:
        pairs = [p for p in pairs if p.genre == args.genre]
    stats = summarise(pairs)
    _print_stats(stats)
    _warn_low_volume(stats)

    if stats.total == 0:
        print("ERROR: no training pairs after loading/filtering; aborting.", file=sys.stderr)
        return 2

    cfg = TrainerConfig(
        pairs=pairs,
        base_model=args.base,
        out_dir=args.out,
        iters=args.iters,
        batch_size=args.batch_size,
        genre=args.genre,
        include_genre_tag=args.include_genre_tag,
        seed=args.seed,
    )
    trainer_fn = _fake_smoke_trainer if args.smoke else None
    result: TrainingResult = run_training(cfg, trainer_fn=trainer_fn)
    print(f"adapter written to: {result.adapter_path}")
    print(f"stats: {result.stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/training/test_cli.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/training/cli.py tests/training/test_cli.py
git commit -m "feat(training): sidequest-train CLI with --smoke mode for scaffolding"
```

---

### Task 18: End-to-end smoke against the real CLI entrypoint

**Files:** none beyond validation.

- [ ] **Step 1: Install the console script**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon/.worktrees/group-e
uv sync --extra training
```

- [ ] **Step 2: Run the CLI in smoke mode end-to-end**

```bash
uv run sidequest-train \
  --corpus ~/.sidequest/corpus/mined/*.jsonl \
  --base Qwen/Qwen2.5-7B-Instruct \
  --out ~/.sidequest/loras/smoke \
  --iters 1 \
  --batch-size 1 \
  --smoke
```

Expected: prints corpus stats, emits a low-volume warning if corpus is thin, writes an `adapters.safetensors` file under `~/.sidequest/loras/smoke/Qwen2.5-7B-Instruct-<ts>/`.

If `~/.sidequest/corpus/mined/` is empty, substitute the repo fixture:

```bash
uv run sidequest-train \
  --corpus tests/training/fixtures/mined_sample.jsonl \
  --base Qwen/Qwen2.5-7B-Instruct \
  --out /tmp/sidequest-train-smoke \
  --iters 1 --batch-size 1 --smoke
```

- [ ] **Step 3: Verify adapter file appears**

```bash
find ~/.sidequest/loras/smoke /tmp/sidequest-train-smoke -name "adapters.safetensors" 2>/dev/null
```

Expected: at least one hit.

- [ ] **Step 4: Commit a smoke record**

```bash
git commit --allow-empty -m "chore(training): smoke-mode CLI e2e verified (no real training ran)"
```

---

### Task 19: Docs + daemon-side PR

**Files:**
- Create: `sidequest-daemon/docs/training.md`
- Modify: `sidequest-daemon/README.md`

- [ ] **Step 1: Write the training doc**

Save as `sidequest-daemon/docs/training.md`:

```markdown
# Training Pipeline (ADR-073 Phase 3)

`sidequest-train` fine-tunes a QLoRA adapter against Group D corpus data.

## Install

```
cd sidequest-daemon
uv sync --extra training
```

This adds `mlx-lm>=0.20` (macOS/Apple Silicon only).

## Usage

```
uv run sidequest-train \
  --corpus ~/.sidequest/corpus/mined/*.jsonl \
  --base Qwen/Qwen2.5-7B-Instruct \
  --out ~/.sidequest/loras/caverns_and_claudes \
  --genre caverns_and_claudes \
  --include-genre-tag \
  --iters 600 \
  --batch-size 4
```

Flags:
- `--corpus` — one or more JSONL files from `~/.sidequest/corpus/mined/`
- `--base` — HF model id passed straight to `mlx-lm`
- `--out` — adapters land under `<out>/<model-slug>-<ts>/adapters.safetensors`
- `--genre` — filter corpus to a single genre slug (optional)
- `--include-genre-tag` — prepend `[genre=X]` to system prompt in training data
- `--iters`, `--batch-size`, `--seed` — standard mlx-lm knobs
- `--smoke` — skip real training; write a dummy adapter (used in CI and for pipeline shake-down)

## Corpus volume

ADR-073 calls for ~5K pairs minimum for base fine-tune, ~500 per genre for
LoRA. Below 500 total the CLI prints a loud overfit warning — training still
runs, but the adapter will not generalise.

## Deployment (not wired in Group E)

The output `adapters.safetensors` is an MLX adapter. Serving it via Ollama
requires GGUF conversion, which is explicitly out of scope for Group E.
Deployment will be addressed in a future plan.
```

- [ ] **Step 2: Point the README at the new doc**

In `sidequest-daemon/README.md`, append:

```markdown
## Training pipeline

See `docs/training.md` for `sidequest-train` usage (ADR-073 Phase 3).
```

- [ ] **Step 3: Open the PR**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon/.worktrees/group-e
git add -A
git commit -m "docs(training): sidequest-train CLI usage + corpus volume guidance"
just daemon-test 2>/dev/null || uv run pytest -q
just daemon-lint 2>/dev/null || uv run ruff check sidequest_daemon tests
git push -u origin feat/local-dm-group-e-daemon
gh pr create --base develop --title "feat: local DM group E (daemon) — MLX-LM training pipeline" --body "$(cat <<'EOF'
## Summary

Ships ADR-073 Phase 3 training pipeline.

- `sidequest_daemon/training/` — corpus loader, Qwen ChatML formatter, trainer wrapper, `sidequest-train` CLI.
- `mlx-lm>=0.20` added as an optional `training` extra.
- `--smoke` mode verifies pipeline plumbing end-to-end without running GPU work.
- Docs: `docs/training.md`.

Serving the trained adapter via Ollama is **not** shipped — GGUF conversion is out of scope, documented as future work.

## Test plan
- [x] `uv run pytest` green
- [x] `uv run sidequest-train --smoke` writes adapter file
EOF
)"
```

---

## Self-Review

**Spec coverage check (ADR-073):**

- Phase 1 (LlmClient trait extraction) — Tasks 2–5. `LlmClient` Protocol, `LlmCapabilities`, `LlmResponse`/`ClaudeResponse` with `backend` tag, OTEL span tagging, factory wiring. ADR's `SessionContext` + `ModelHint` nested types are collapsed: `session_id` + `history` are handled inside each backend (Ollama stores history locally; Claude uses `--resume`), and `model_hint` is just the existing `model` string plus the Ollama `model_map` translation layer. **Covered.**
- Phase 2 (Ollama/MLX backends) — Tasks 6–10. Ollama: covered. **MLX backend deferred** — explicit non-goal, documented in "Decisions locked" #9 and "Non-goals".
- Phase 3 (QLoRA fine-tune pipeline) — Tasks 13–19. Corpus loader, formatter, trainer, CLI, smoke validation. **Adapter serving is out of scope** — documented.
- Phase 0 (TurnRecord capture) — **already landed via Group D** (`sidequest/corpus/` reads `~/.sidequest/saves/**/save.db` directly; ADR's JSONL-during-play capture was superseded by save-file mining). No task here.

**Placeholder scan:**
- No "TBD" / "TODO" / "implement later" / "add appropriate error handling" / "similar to Task N" strings.
- Every code block contains the literal code the engineer needs.
- Every command block contains the exact command + expected output.

**Type consistency check:**
- `LlmClient` Protocol is the single name throughout Phase 1+2.
- `ClaudeResponse` keeps its name; extended with `backend` field in Task 3; used by `OllamaClient` in Tasks 6–8.
- `LlmCapabilities` dataclass definition in Task 2 matches every reference in later tasks (`backend_id`, `supports_sessions`, `supports_tools`, `max_context_tokens`, `supports_streaming`).
- `TrainingPair` schema locally mirrored in `sidequest_daemon/training/corpus_loader.py` — intentionally duplicated from server to avoid cross-repo imports; field names match Group D schema exactly.
- `TrainerConfig`, `TrainerFn`, `TrainingResult` names are stable across Tasks 16–17.
- CLI flag names (`--corpus`, `--base`, `--out`, `--iters`, `--batch-size`, `--smoke`, `--genre`, `--include-genre-tag`, `--seed`) match between Task 17 implementation and Task 19 docs.

**Spec gaps:**
- No gap — every ADR-073 deliverable lands or is explicitly scoped out with a decision-log entry.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-23-local-dm-group-e-llm-backends.md`. Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. Works well given three clean phase boundaries and cross-repo worktrees.
2. **Inline Execution** — Work the tasks in the current session with `superpowers:executing-plans`, checkpoint between tasks.

Which approach?
