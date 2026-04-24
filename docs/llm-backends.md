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
