# ADR-012: Agent Session Management

> Ported from sq-2. Rust adaptation: `tokio::process::Command` with timeout.

## Status
Accepted

## Context
Claude CLI supports persistent sessions via `--session-id`. This enables conversational continuity across turns without re-sending full context.

## Decision
Each agent maintains a persistent Claude CLI session. First call establishes the session with a system prompt; subsequent calls resume.

### Lifecycle
1. **First call:** `claude -p "{prompt}" --system "{system}" --session-id "{id}"`
2. **Subsequent:** `claude -p "{prompt}" --resume --session-id "{id}"`
3. **Stale recovery:** If Claude returns "No conversation found", retry with fresh session

### Rust Pattern
```rust
pub struct Agent {
    pub name: String,
    pub system_prompt: String,
    pub session_id: String,
    pub timeout: Duration,
    initialized: bool,
}

impl Agent {
    pub async fn send(&mut self, message: &str) -> Result<String, AgentError> {
        let mut cmd = Command::new("claude");
        cmd.args(["-p", message]);

        if self.initialized {
            cmd.args(["--resume", "--session-id", &self.session_id]);
        } else {
            cmd.args(["--system", &self.system_prompt, "--session-id", &self.session_id]);
            self.initialized = true;
        }

        let output = tokio::time::timeout(self.timeout, cmd.output())
            .await
            .map_err(|_| AgentError::Timeout)??;

        let text = String::from_utf8_lossy(&output.stdout).trim().to_string();

        // Stale session recovery
        if text.contains("No conversation found") {
            self.initialized = false;
            return self.send(message).await;
        }

        Ok(text)
    }
}
```

### Timeout
120s per call. Configurable per agent type.

### Execution Modes
- **Headless:** Default production mode (`claude -p`)
- **Tmux:** Visible panes for debugging (future)

## Consequences
- Agents remember conversation context across turns
- Stale sessions self-heal without player intervention
- Session IDs are UUID-based, scoped to the game session
