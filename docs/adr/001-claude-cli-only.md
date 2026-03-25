# ADR-001: Claude CLI Only

> Ported from sq-2. Rust adaptation: `tokio::process::Command` replaces `asyncio.create_subprocess_exec`.

## Status
Accepted

## Context
SideQuest runs on Claude Max (unlimited usage), not API credits. All LLM calls must use the `claude -p` CLI subprocess.

## Decision
All LLM calls use `claude -p` via `tokio::process::Command`. No Anthropic SDK dependency.

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
- **Cost:** Zero — Claude Max subscription covers all usage
- **Latency:** ~200ms overhead per call (subprocess spawn)
- **Streaming:** Not supported via `-p` (full response only)
- **Concurrency:** Multiple subprocesses OK; Claude CLI handles queueing
- **Testing:** Mock via trait boundary, not HTTP intercept
- **Enforcement:** Clippy lint or test scanning for banned `anthropic` crate imports
