---
id: 1
title: "Claude CLI Only"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [73, 82]
tags: [core-architecture]
implementation-status: live
implementation-pointer: null
---

# ADR-001: Claude CLI Only

## Implementation status (2026-05-02)

The truly load-bearing constraint of this ADR is **no Anthropic SDK dependency** — that constraint remains absolute and is enforced by the absence of `from anthropic` / `import anthropic` / `@anthropic-ai/sdk` anywhere in `sidequest-server`, `sidequest-daemon`, or `sidequest-ui`. The grep is the test.

Two things have evolved since 2026-03-25 and the ADR body below is no longer a faithful description of current code:

- **Default backend is Python, not Rust.** Per ADR-082, `sidequest-api` (Rust) was reverted to `sidequest-server` (Python). The live transport is `asyncio.create_subprocess_exec` in `sidequest-server/sidequest/agents/claude_client.py` (`_default_spawner` at the module level, `ClaudeClient` class). The Rust `tokio::process::Command` example in the Decision section is port-era residue and should be read as historical only.
- **`claude` is the default backend, not the only one.** Per ADR-073 Phase 1/2, Ollama is a permitted alternative LLM backend selected via `SIDEQUEST_LLM_BACKEND={claude,ollama}` (default `claude`). See `sidequest-server/sidequest/agents/llm_factory.py` and `sidequest-server/sidequest/agents/ollama_client.py`. The literal claim "All LLM calls use `claude -p`" in the original Decision is no longer true — the load-bearing absolute is the SDK-ban, not the binary.

The original 2026-03-25 decision is preserved below for historical context.

## Context
SideQuest runs on Claude Max (unlimited usage), not API credits. All LLM calls must use the `claude -p` CLI subprocess.

## Decision
All LLM calls use `claude -p` via `tokio::process::Command`. No Anthropic SDK dependency.

> **Historical context (port era).** The Rust example below was written during the brief Rust era (2026-03-30 to 2026-04-19) and is preserved as a record of the original decision. The current Python implementation lives in `sidequest-server/sidequest/agents/claude_client.py`; see the Implementation status section above.

```rust
use tokio::process::Command;

pub async fn call_claude(prompt: &str, system: &str) -> Result<String, AgentError> {
    let output = Command::new("claude")
        .args(["-p", prompt, "--system", system])
        .output()
        .await
        .map_err(AgentError::Spawn)?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(AgentError::NonZeroExit(stderr.to_string()));
    }

    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}
```

## Consequences
- **Cost:** Zero — Claude Max subscription covers all usage (still true; Ollama backend is local/free)
- **Latency:** ~200ms overhead per call (subprocess spawn for the Claude CLI path)
- **Streaming:** Not supported via `-p` (full response only) — see also `project_claude_p_no_reactive_tools` constraint: `claude -p` cannot call tools mid-generation
- **Concurrency:** Multiple subprocesses OK; Claude CLI handles queueing
- **Testing:** Mock via the `LlmClient` protocol boundary, not HTTP intercept
- **Enforcement:** Grep for banned `anthropic` SDK imports across all subrepos — no Clippy lint required since the tree is now Python
