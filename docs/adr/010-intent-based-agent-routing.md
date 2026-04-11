# ADR-010: Intent-Based Agent Routing

> Ported from sq-2. Language-agnostic agent architecture.

## Status
**Superseded by [ADR-067: Unified Narrator Agent](067-unified-narrator-agent.md)** (2026-04)

> **Note (2026-04-11):** ADR-067 collapses the specialist-agent dispatch
> described below into a single persistent Opus narrator session. The
> CombatAgent / NPCAgent / specialist mappings in the table that follows no
> longer reflect runtime behavior. The Rust crate `sidequest-agents` no longer
> contains `creature_smith`, `dialectician`, or `ensemble` modules. An
> `intent_router` file remains as a transitional fallback but is not part of
> the steady-state design. This ADR is preserved as the historical rationale
> for why specialist routing existed before ADR-066's persistent-session
> capability made it unnecessary.

## Context
Player input is ambiguous. "Draw my sword" means different things in combat vs. a social scene. Keywords and regex can't resolve context-dependent intent.

## Decision
An LLM classifier routes each player input to a specialist agent based on intent and current game state.

### Intent Categories

| Intent | Agent | Example |
|--------|-------|---------|
| combat | CombatAgent | "I attack the goblin" |
| dialogue | NPCAgent | "I ask the innkeeper about rumors" |
| exploration | Narrator | "I head north toward the mountains" |
| examine | Narrator | "I look around the room" |
| inventory | Narrator (w/ rules) | "I use the healing potion" |
| world_query | Narrator | "What do I know about this place?" |
| meta | System | "Save game", "Help" |

### Pattern
```rust
pub struct IntentRouter {
    system_prompt: String,
}

impl IntentRouter {
    pub async fn classify(&self, input: &str, state: &GameState) -> Result<IntentRoute> {
        let prompt = format!(
            "Player input: {input}\nGame state: {state_summary}\nClassify intent.",
        );
        let response = call_claude(&prompt, &self.system_prompt).await?;
        parse_intent(&response)
    }
}
```

### Cost
~1-2s latency per classification (one Claude CLI call). This is on the critical path but necessary — keyword matching was tried and rejected due to ambiguity.

## Consequences
- Routing is context-aware (same words, different routes based on state)
- One extra LLM call per turn on the critical path
- Fallback: if classification fails, default to Narrator
