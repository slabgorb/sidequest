---
parent: context-epic-1.md
---

# Story 1-5: Prompt Composer + Agent Framework — Attention Zones, Rule Taxonomy, SOUL.md, ClaudeClient

## Business Context

Port `prompt_composer.py`, `prompt_builder.py`, `agents/claude_agent.py`, and the agent
interface pattern. The prompt composer is one of the most sophisticated parts of the
Python codebase — it uses attention-zone ordering to exploit LLM primacy/recency bias,
a three-tier rule taxonomy with genre pack overrides, and section-based prompt assembly.
This is a proven design that should be ported faithfully.

**Python sources:**
- `sq-2/sidequest/prompt_composer.py` — PromptComposer, GamePromptComposer, PromptSection,
  SectionCategory, SectionZone, attention-zone assembly (~928 lines)
- `sq-2/sidequest/prompt_builder.py` — per-agent context building
- `sq-2/sidequest/agents/claude_agent.py` — ClaudeAgent subprocess wrapper
- `sq-2/sidequest/agents/narrator.py` — example agent (format helpers, system prompt)
- `sq-2/sidequest/agents/format_helpers.py` — shared formatting functions
- `sq-2/sidequest/orchestrator.py` — Orchestrator (state machine + context composer)
- `sq-2/sidequest/soul.py` — SOUL.md parser
- `sq-2/docs/SOUL.md` → `oq-2/docs/SOUL.md` — agent guidelines (runtime data)

## Technical Guardrails

- **SOUL.md is runtime data.** The GamePromptComposer takes `soul_path: Path`, calls
  `parse_soul_md()`, and injects the principles as a PromptSection in the EARLY zone.
  Individual agents never touch SOUL.md. Load from configurable path, not embedded
- **Port the attention zones faithfully:**
  - PRIMACY: agent identity, agency rules (highest attention)
  - EARLY: SOUL principles, genre tone, genre rules
  - VALLEY: lore, geography, tropes, other characters (low attention)
  - LATE: game state, active character, scene pacing (high recency)
  - RECENCY: `<before-you-respond>` self-check (highest)
- **Three-tier rule taxonomy:** critical (all agents), firm (per-agent), coherence
  (per-agent). Genre packs can override by rule name
- **Port lesson #2 (single JSON extractor):** Python has the same 3-tier extraction logic
  duplicated 4+ times. Create one `JsonExtractor` in the agents crate
- **Port lesson #3 (single ClaudeClient):** Python has 3 different subprocess patterns
  with different timeouts (120s, 30s, none). Create one `ClaudeClient` with configurable
  timeout, consistent error types, and a standard fallback policy
- **Port lesson #7 (Agent trait):** Define a proper trait:
  ```
  trait Agent {
      fn name(&self) -> &str;
      fn system_prompt(&self) -> &str;
      fn build_context(&self, state: &GameSnapshot) -> Context;
      async fn execute(&self, client: &ClaudeClient, context: Context) -> Result<AgentResponse>;
  }
  ```
- **Port lesson #8 (ContextBuilder):** Python agents manually assemble context by calling
  format helpers in different orders. Create a ContextBuilder with composable sections

### Agent types to port

| Agent | Python Source | Purpose |
|-------|-------------|---------|
| Narrator | `agents/narrator.py` | Exploration, narration, consequences |
| Combat | `agents/combat.py` | Combat mechanics, enemy actions |
| NPC | `agents/npc.py` | NPC dialogue and actions |
| WorldState | `agents/world_state.py` | State patches, world mutations |
| Chase | `agents/chase.py` | Chase sequence narration |
| IntentRouter | `agents/intent_router.py` | Route player input to right agent |
| PerceptionRewriter | `agents/perception_rewriter.py` | Per-character perception |
| MusicDirector | `agents/music_director.py` | Audio mood selection |

### Orchestrator

Port `orchestrator.py` (~900 lines). This is the state machine that:
1. Receives player input
2. Routes to the right agent via IntentRouter
3. Composes context via GamePromptComposer
4. Calls Claude CLI via ClaudeClient
5. Validates and applies state patches
6. Emits messages to the server

The Orchestrator implements the `GameService` trait that story 1-6 (server) depends on.

## Scope Boundaries

**In scope:**
- PromptSection, SectionCategory, SectionZone types
- GamePromptComposer with full attention-zone assembly
- Three-tier rule taxonomy with genre pack merge
- SOUL.md parser and injection
- ClaudeClient (tokio::process::Command wrapper with configurable timeout)
- JsonExtractor (single implementation)
- Agent trait definition
- All 8 agent type implementations
- ContextBuilder with composable sections
- Orchestrator (state machine, agent routing, patch application)
- GameService trait (facade for server)
- Format helpers (ported from format_helpers.py)

**Out of scope:**
- WebSocket transport (story 1-6)
- Lore RAG retrieval (future epic — use StaticLoreRetriever pattern)
- Media pipeline integration (daemon territory)

## AC Context

| AC | Detail |
|----|--------|
| Attention zones | PromptSection with 5 zones, assembled in primacy→recency order |
| Rule taxonomy | Three tiers (critical/firm/coherence) with genre pack overrides |
| SOUL.md loaded | Parsed from configurable path, injected in EARLY zone |
| ClaudeClient | Single subprocess wrapper with configurable timeout and error types |
| JsonExtractor | Single 3-tier extraction (direct → fence → freeform) |
| Agent trait | All 8 agents implement the trait with consistent interface |
| Orchestrator | State machine routes input, calls agents, applies patches |
| GameService trait | Facade trait that server depends on |
| ContextBuilder | Composable sections replace manual format-helper assembly |
