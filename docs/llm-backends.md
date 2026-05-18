# LLM Backend Configuration

> Narrator LLM transport, model routing, and backend selection.
> Source of truth: `sidequest-server/sidequest/agents/llm_factory.py`,
> `anthropic_sdk_client.py`, `model_routing.py`, `anthropic_cost.py`.
>
> **Last updated:** 2026-05-18
> **Doctrine:** ADR-101 (SDK backend, supersedes ADR-001), ADR-102 (native
> tool-use, supersedes ADR-039), ADR-103 (native OTEL via tool registry,
> supersedes ADR-058). Phase D — SDK is live and default on `develop`.

## TL;DR

The narrator path uses the **Anthropic Python SDK by default** (`anthropic_sdk`).
Two opt-in fallbacks survive — `claude` (CLI subprocess) and `ollama` — and
`claude -p` still serves a few non-narrator jobs (notably daemon-side subject
extraction and the dungeon "curate" stage). `ANTHROPIC_API_KEY` is a **hard
runtime requirement** on the SDK path — fail-loud, no silent fallback.

## Environment Variables

| Variable | Values | Default | Notes |
|----------|--------|---------|-------|
| `SIDEQUEST_LLM_BACKEND` | `anthropic_sdk` \| `claude` \| `ollama` | `anthropic_sdk` | Unknown values raise `UnknownBackend` at startup |
| `ANTHROPIC_API_KEY` | API key | unset | Required on `anthropic_sdk` and for the ADR-107 aside resolver — both fail loudly if missing |
| `SIDEQUEST_OLLAMA_URL` | Any URL | `http://localhost:11434` | Only consulted on `ollama` |

There is no silent demotion: if `ANTHROPIC_API_KEY` is missing and the backend
is `anthropic_sdk`, the process fails on the first narrator turn rather than
quietly downgrading to `claude -p`. This is intentional per CLAUDE.md's "No
Silent Fallbacks" rule.

## Backend Roster

### `anthropic_sdk` (default — ADR-101)

Wraps `anthropic.AsyncAnthropic` in `agents/anthropic_sdk_client.py`. Returns a
`ToolingLlmClient` — a richer protocol than the legacy `LlmClient` because
narrator turns now run a tool-use loop, not a single completion. Three
load-bearing features:

1. **Prompt caching.** `cache_control` breakpoints on the three stable system
   zones (SOUL + rules, tool definitions, world snapshot) yield ~60% cached
   input after warmup. Beta header `extra-cache-ttl-2025-04-11` is sent so
   `ttl: "1h"` ephemeral cache works; without it, every narration turn 400s.
2. **Native tool-use (ADR-102).** Mechanical state changes are produced as
   JSON-Schema-validated tool calls — the narrator structurally cannot
   describe an item, mood, intent, SFX, render, or resource delta without
   invoking the matching tool. This replaces the ADR-039 fenced-JSON sidecar
   that the `claude -p` path relied on. `assemble_turn` merges tool results
   with prose; tool values take precedence over any prose extraction.
3. **Per-call model routing (ADR-101).** Each call picks a model from the
   Claude 4.x family by purpose — see the next section.

### `claude` (opt-in — legacy, ADR-001 superseded by ADR-101)

CLI subprocess wrapper in `agents/claude_client.py`. Kept on the narrator path
as a fallback and used for:

- Daemon-side subject extraction (prose → visual description for the image
  pipeline).
- The dungeon "curate" stage (ADR-106 megadungeon authoring pass) — currently
  the only LLM call in the procedural megadungeon expansion loop.

Returns a plain `LlmClient` — no tool-use, no caching. ADR-039's fenced-JSON
sidecar is the only way to get structured output on this backend, and it is
**off by default**: only the legacy `SIDEQUEST_NARRATOR_STREAMING=1` mode
turns it back on.

### `ollama` (opt-in — local inference, ADR-073 lineage)

HTTP client in `agents/ollama_client.py`. Hits a local Ollama server at
`SIDEQUEST_OLLAMA_URL`. Returns a plain `LlmClient`. No prompt caching, no
tool-use, no model routing. Capabilities are advertised via
`LlmClient.capabilities()` and tagged on OTEL spans as `agent.backend`, but
the orchestrator does not route on them — prompt-tier selection ignores
backend.

Testable without a real server: `OllamaClient(http_fn=...)` accepts an
injected transport. See `tests/agents/test_ollama_client.py::_FakeHttpResponse`.

#### Ollama install (macOS)

```bash
brew install ollama
ollama serve &
ollama pull qwen2.5:7b-instruct
ollama create sidequest-narrator -f Modelfile-narrator   # optional alias
```

Real fine-tuned adapters are out of scope post-port; `sidequest-narrator:latest`
points at the base Qwen model and narration quality will be visibly below the
SDK path. The daemon-side training pipeline (corpus gate → GGUF convert →
Ollama Modelfile deploy, story 48-3) ships with `sidequest-deploy` as the
console entry point — see `sidequest-daemon/sidequest_daemon/deploy/`.

## Per-Call Model Routing (ADR-101)

The SDK backend picks a model per call, not per session. Defaults live in
`agents/model_routing.py`:

| Call site | Model | Why |
|-----------|-------|-----|
| Intent classification / scratch | Haiku 4.5 (`claude-haiku-4-5-20251001`) | Cheap, fast, sufficient for state-override and short structured calls |
| Aside resolver (ADR-107) | Haiku 4.5 | An aside is the lowest-drama input in the system per SOUL.md "Cost Scales with Drama" — single-shot completion, not the tool-use loop |
| Default narration | Sonnet 4.6 | Quality / cost balance for ordinary turns |
| Declared-important moments | Opus 4.7 | Drama spikes, milestones, set-piece scenes |

Drama-driven escalation is read from `TensionTracker.drama_weight` plus the
narrator's own opt-in "this is important" signal carried in tool results.
There is no automatic Opus-everywhere mode; cost matters.

## Cost Telemetry

`agents/anthropic_cost.py` computes per-call USD from the SDK response's
input/output token counts (including cache hits and cache writes). The
`llm.request` OTEL span carries `model`, `input_tokens`, `output_tokens`,
`cache_read_tokens`, `cache_write_tokens`, and `cost_usd` — these surface in
the GM dashboard so Keith (and Sebastien — see CLAUDE.md "Who This Is For")
can see what a turn cost in real time.

ADR-103 made OTEL **native** to the tool registry — every tool invocation
emits a span automatically, no scraper, no post-hoc parsing of CLI output.
The old ADR-058 `playtest_otlp` Claude-subprocess HTTP/JSON stream still
exists for the dashboard's legacy panes but no longer reflects narrator state
on the SDK path; narrator spans flow `server-tracer → gRPC → Jaeger` instead.

## Capabilities Protocol

Each backend advertises capabilities via `LlmClient.capabilities()` (see
`agents/claude_client.py::LlmCapabilities`). The orchestrator does not
currently branch on these — backend selection is pre-startup — but every
OTEL span carries `agent.backend` so the GM panel can tell which transport
served a given turn. This is the lie-detector path for "is the SDK actually
live or did we silently fall through to `claude -p`?"

## Failure Modes (No Silent Fallbacks)

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Server fails on first narrator turn with `LlmClientError: ANTHROPIC_API_KEY not set` | Missing key on `anthropic_sdk` path | Export the key; do not fall back to `claude -p` silently |
| Every turn 400s on the SDK path | Beta cache header dropped | Verify `extra-cache-ttl-2025-04-11` is sent (see `anthropic_sdk_client.py`) |
| Narrator emits raw JSON in prose on `anthropic_sdk` | Tool-use loop didn't converge — `AnthropicSdkLoopExceeded` | Check tool schemas; the loop is bounded by `max_iterations` |
| Server starts but `SIDEQUEST_LLM_BACKEND=foo` was set | `UnknownBackend` raised at boot | Use one of `anthropic_sdk`, `claude`, `ollama` |
| Aside (ADR-107) fails with `ANTHROPIC_API_KEY not set` even though narrator works | Aside resolver constructs a separate `AsyncAnthropic`; both narrator and aside need the key | Export the key once for both call sites |

## Related ADRs

- **ADR-101** — Anthropic SDK as Narrator Backend (supersedes ADR-001)
- **ADR-102** — Tool-Use Protocol for Structured Output (supersedes ADR-039)
- **ADR-103** — Native OTEL via Tool Registry (supersedes ADR-058)
- **ADR-067** — Unified Narrator Agent (collapses ADR-010 multi-agent dispatch)
- **ADR-098** — Stateless Narrator Turns (supersedes ADR-066 persistent sessions)
- **ADR-107** — Out-of-Band Aside Channel (separate Haiku call site)
- **ADR-073** — Local Fine-Tuned Model Architecture (Ollama backend lineage)
