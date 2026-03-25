---
parent: context-epic-2.md
---

# Story 2-6: Agent Execution — Claude CLI Subprocess Calls, Prompt Composition with Genre/State Context, JSON Extraction

## Business Context

Story 1-10 built the `ClaudeClient` subprocess wrapper and the prompt framework with
attention zones. Story 1-11 built the 8 agent implementations with system prompts. This
story makes them actually run: compose full prompts with genre pack data and live game state,
call `claude -p` as a subprocess, parse the response, and extract JSON patches when present.

This is where the abstract agent infrastructure becomes a working AI pipeline. The Python
implementation calls Claude via subprocess with carefully ordered prompts — we port that
exact pattern but with typed prompt sections instead of string concatenation.

**Python source:** `sq-2/sidequest/agents/claude_agent.py` (ClaudeAgent.send, _send_headless, send_streaming)
**Python source:** `sq-2/sidequest/prompt_composer.py` (GamePromptComposer._assemble_sections)
**Python source:** `sq-2/sidequest/orchestrator.py` lines 1359-1400 (agent dispatch, patch extraction)
**ADRs:** ADR-005 (Claude CLI, not SDK), ADR-008 (three-tier prompt taxonomy), ADR-009 (attention zones), ADR-012 (agent sessions), ADR-013 (lazy JSON extraction)
**Depends on:** Story 2-5 (orchestrator turn loop, calls agents through this layer)

## Technical Approach

### What Python Does

```python
class ClaudeAgent:
    async def _send_headless(self, message):
        cmd = [
            "claude", "--setting-sources", "user",
            "-p", message,
            "--system-prompt", self.system_prompt,
            "--output-format", "json",
            "--permission-mode", "bypassPermissions",
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            raise AgentError(f"Exit {proc.returncode}: {stderr}")
        parsed = json.loads(stdout)
        return parsed.get("result", stdout.decode())
```

```python
class GamePromptComposer:
    def _assemble_sections(self, agent_name, state, ...):
        sections = []
        # PRIMACY: role definition, agency rules
        # EARLY: soul principles, genre tone, genre rules
        # VALLEY: lore, geography, factions, active tropes
        # LATE: NPCs, game state, active character, output format
        # RECENCY: self-check block
        return sorted(sections, key=lambda s: s.zone.value)
```

The problems:
- System prompt is rebuilt from scratch every turn — the entire prompt composer runs again
- No caching of prompt sections that don't change (soul, genre tone, rules)
- `send_streaming` and `_send_headless` duplicate the subprocess logic
- JSON extraction is done per-agent with duplicate regex patterns
- Session ID management (ADR-012) is manual and error-prone

### What Rust Does Differently

**Subprocess call via `tokio::process::Command`:**

```rust
impl ClaudeClient {
    pub async fn send(
        &self,
        system_prompt: &str,
        user_message: &str,
    ) -> Result<String, ClaudeClientError> {
        let mut cmd = Command::new(&self.command_path);
        cmd.args(["--setting-sources", "user"])
           .args(["-p", user_message])
           .args(["--system-prompt", system_prompt])
           .args(["--output-format", "json"])
           .args(["--permission-mode", "bypassPermissions"]);

        if let Some(model) = &self.model {
            cmd.args(["--model", model]);
        }

        cmd.stdout(Stdio::piped()).stderr(Stdio::piped());

        let child = cmd.spawn().map_err(|e| ClaudeClientError::SubprocessFailed {
            exit_code: -1,
            stderr: e.to_string(),
        })?;

        let output = tokio::time::timeout(self.timeout, child.wait_with_output())
            .await
            .map_err(|_| ClaudeClientError::Timeout)?
            .map_err(|e| ClaudeClientError::SubprocessFailed {
                exit_code: -1,
                stderr: e.to_string(),
            })?;

        if !output.status.success() {
            return Err(ClaudeClientError::SubprocessFailed {
                exit_code: output.status.code().unwrap_or(-1),
                stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
            });
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        self.parse_json_envelope(&stdout)
    }
}
```

**This is already scaffolded in story 1-10.** This story fills in the actual subprocess
invocation and adds streaming support.

**Streaming subprocess:**

```rust
pub async fn send_streaming(
    &self,
    system_prompt: &str,
    user_message: &str,
    chunk_tx: mpsc::Sender<String>,
) -> Result<String, ClaudeClientError> {
    let mut cmd = Command::new(&self.command_path);
    cmd.args(["--setting-sources", "user"])
       .args(["-p", user_message])
       .args(["--system-prompt", system_prompt])
       .args(["--output-format", "stream-json"])
       .args(["--verbose"])
       .args(["--permission-mode", "bypassPermissions"]);

    // Read stdout line by line, parse NDJSON events
    // Filter for type == "assistant", yield content[].text chunks
    // Also collect full response for post-processing
}
```

Python's `send_streaming` yields chunks via `async for`. Rust sends chunks through an
`mpsc::Sender` — the orchestrator forwards them to the server, which sends NARRATION_CHUNK
messages.

### Prompt Composition

The prompt composer assembles sections in attention-zone order (ADR-009):

```rust
impl PromptComposer {
    pub fn compose(
        &self,
        agent: AgentKind,
        state: &GameState,
        genre_pack: &GenrePack,
    ) -> String {
        let mut sections: Vec<PromptSection> = Vec::new();

        // PRIMACY (highest attention — read first by LLM)
        sections.push(self.role_definition(agent));
        sections.push(self.agency_rules());

        // EARLY (genre context)
        sections.push(self.soul_principles());
        sections.push(self.genre_tone(agent, genre_pack));
        sections.push(self.genre_rules(genre_pack));

        // VALLEY (background reference — lowest attention)
        if let Some(lore) = self.lore_section(genre_pack) {
            sections.push(lore);
        }
        sections.push(self.active_tropes(state));

        // LATE (per-turn state — high attention)
        sections.push(self.game_state_section(state));
        sections.push(self.active_character_section(state));
        self.agent_specific_sections(agent, state, genre_pack, &mut sections);

        // RECENCY (read last — highest attention)
        sections.push(self.self_check_block(agent));

        // Sort by zone, format as XML-tagged sections
        sections.sort_by_key(|s| s.zone);
        sections.iter()
            .map(|s| format!("<section name=\"{}\" category=\"{:?}\">\n{}\n</section>",
                             s.name, s.category, s.content))
            .collect::<Vec<_>>()
            .join("\n\n")
    }
}
```

**Type-system win:** `PromptSection` has typed `zone: AttentionZone` and
`category: SectionCategory` — both enums from story 1-9. The sort is by enum discriminant,
not string comparison. Adding a new zone is a compiler-forced change everywhere.

**Section caching:** Genre-invariant sections (soul principles, agency rules, role definitions)
are computed once at genre-bind time and reused. Only state-dependent sections (game state,
active character, NPCs) are rebuilt per turn. Python recomputes everything every turn.

### JSON Extraction (ADR-013)

Three-tier fallback for parsing JSON from agent responses:

```rust
pub fn extract_json<T: DeserializeOwned>(raw: &str) -> Option<T> {
    // Tier 1: Direct parse
    if let Ok(parsed) = serde_json::from_str::<T>(raw) {
        return Some(parsed);
    }

    // Tier 2: Extract from ```json ... ``` fence
    if let Some(fenced) = extract_fenced_json(raw) {
        if let Ok(parsed) = serde_json::from_str::<T>(&fenced) {
            return Some(parsed);
        }
    }

    // Tier 3: Find first { ... } block via brace matching
    if let Some(block) = extract_first_json_block(raw) {
        if let Ok(parsed) = serde_json::from_str::<T>(&block) {
            return Some(parsed);
        }
    }

    None  // All tiers failed
}
```

**This is already scaffolded in story 1-10 as `JsonExtractor`.** This story wires it to the
actual agent response handling.

**Type-system win:** `extract_json<T>` is generic over the target type. Python's extraction
returns `dict` and then validates separately. Rust deserializes directly to the typed struct
— if the JSON doesn't match `CombatPatch` fields, it fails at extraction, not later when
you access a missing key.

### SOUL.md Loading

SOUL.md is runtime data injected into every agent's system prompt. The parser is already
built in story 1-9. This story wires it:

```rust
let soul = Soul::load_from_file(&genre_packs_path.join("SOUL.md"))?;
// soul.principles: Vec<SoulPrinciple> — injected into EARLY zone
```

### Agent Session Management (ADR-012)

Python maintains persistent Claude sessions with `--session-id` and `--resume`. The Rust
version starts simpler: each agent call is stateless (no session continuity). This means
each call sends the full system prompt — slightly more tokens but simpler and more reliable.

Session persistence is a future optimization. For the core loop, stateless calls work fine
because the system prompt contains all necessary context.

## Scope Boundaries

**In scope:**
- `ClaudeClient::send()` — actual subprocess execution via `tokio::process::Command`
- `ClaudeClient::send_streaming()` — NDJSON stream parsing, chunk forwarding
- JSON envelope parsing (`{"result": "..."}`)
- `PromptComposer::compose()` — full prompt assembly with genre pack + game state
- Section caching for genre-invariant sections
- `extract_json<T>()` — three-tier JSON extraction wired to typed patches
- SOUL.md loading and injection
- Per-agent system prompts with role definitions from story 1-11

**Out of scope:**
- Agent session persistence (--session-id, --resume — optimization, defer)
- Stale session recovery ("No conversation found" retry)
- TMUX execution mode (dev-only, not core loop)
- Custom timeout per agent type (use global 120s default)
- Hook refinement LLM calls (character creation enhancement, defer)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Agent call works | `ClaudeClient::send()` calls `claude -p`, returns response text |
| Streaming works | `send_streaming()` sends chunks through mpsc, collects full response |
| Timeout handled | Agent call exceeding 120s returns `ClaudeClientError::Timeout` |
| Subprocess error | Non-zero exit code returns `SubprocessFailed` with stderr |
| JSON envelope | `{"result": "narration text"}` parsed, inner text returned |
| Prompt composed | System prompt has sections in attention-zone order with XML tags |
| Genre context | Genre tone, rules, lore included in prompt from loaded GenrePack |
| State context | Current location, characters, NPCs, quests in prompt |
| SOUL injected | SOUL.md principles in EARLY zone of every prompt |
| Combat patch extracted | CreatureSmith response with JSON → `CombatPatch` deserialized |
| Chase patch extracted | Dialectician response with JSON → `ChasePatch` deserialized |
| World patch extracted | WorldBuilder response → `WorldStatePatch` deserialized |
| Extraction fallback | JSON in fenced block or raw { } block extracted successfully |
| Extraction failure | Malformed JSON → None returned, narration preserved |

## Type-System Wins Over Python

1. **Generic `extract_json<T>`** — extraction and validation in one step. Python extracts to dict, then validates.
2. **`PromptSection` with typed zone/category** — sorted by enum, not string. New zones are compile-time changes.
3. **`AgentKind` for dispatch** — no string key lookups. Wrong agent name is a compile error.
4. **`ClaudeClientError` enum** — Timeout, SubprocessFailed, EmptyResponse are distinct. Python catches generic `Exception`.
5. **Section caching is safe** — `Arc<str>` for immutable sections, rebuilt `String` for mutable. No accidental stale state.
