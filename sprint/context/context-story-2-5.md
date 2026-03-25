---
parent: context-epic-2.md
---

# Story 2-5: Orchestrator Turn Loop — Intent Routing, Agent Dispatch, Response Streaming, State Patch, Broadcast

## Business Context

This is the brain of the game engine. The orchestrator takes a player's action, figures out
what kind of action it is (intent routing), sends it to the right Claude agent, streams
the response back, extracts any state patches from the response, applies them, and broadcasts
state updates to the client. It's the `handle_player_input()` method in Python — 170 lines
of carefully ordered steps that this story ports faithfully while enforcing the pipeline
structure with types.

Python's orchestrator is 2500 lines because it also handles media pipelines, speculative
caching, scenario-specific logic, and NPC autonomous actions. We're porting the core turn
loop only — the part that makes "I look around the tavern" produce a narrated response
with state updates.

**Python source:** `sq-2/sidequest/orchestrator.py` (handle_player_input, _route, _build_agent_context)
**Python source:** `sq-2/sidequest/agents/intent_router.py` (IntentRouter.classify)
**Python source:** `sq-2/sidequest/state_processor.py` (StateUpdateProcessor.process_turn)
**ADRs:** ADR-006 (turn phases), ADR-010 (intent routing), ADR-011 (world state patches), ADR-013 (JSON extraction)
**Depends on:** Story 2-2 (session actor, Playing phase)

## Technical Approach

### What Python Does

```python
async def handle_player_input(self, player_input, player_id=None):
    player_input = self._sanitize_player_input(player_input)
    # ... speculative cache check (DEFER)
    # ... slash command check (DEFER)
    route = self._route(player_input)              # intent classification
    session = self.sessions[route.primary_agent]    # get agent session
    session.system_prompt = self.composer.compose_system_prompt(agent_name, self.state, ...)
    context = await self._build_agent_context(agent_name, player_input, player_id)
    # ... inject scenario context (DEFER)
    # ... inject NPC actions (DEFER)
    # ... inject brevity mandate, combat exit summary, etc.
    response = await session.send(context)          # blocking agent call
    if agent_name == "combat":
        response = self._extract_and_apply_combat_patch(response)
    if agent_name == "chase":
        response = self._extract_and_apply_chase_patch(response)
    # ... fire background pipelines (state update, render, audio, voice)
    return response
```

The problems:
- 22 steps in one method, many conditional (scenario, NPC actions, belief cues)
- Agent name is a string key into a dict — typo means KeyError at runtime
- No type for "what comes out of the orchestrator" — it's a string with side effects
- State mutation happens via `self.state` — any step can mutate anything
- "Background pipelines" are fire-and-forget tasks with no error propagation

### What Rust Does Differently

**Typed turn pipeline:**

```rust
pub struct TurnResult {
    pub narration: String,
    pub narration_chunks: Vec<String>,     // for streaming
    pub state_delta: Option<StateDelta>,   // what changed
    pub combat_events: Vec<CombatEvent>,   // if combat state changed
    pub is_degraded: bool,                 // true if agent timed out, used fallback
}
```

Python returns a `str` (the narration text). Rust returns a `TurnResult` that bundles
everything the server needs to broadcast. No side effects — the server reads the result
and sends the appropriate messages.

**Intent routing with typed enum:**

```rust
#[derive(Debug, Clone)]
pub enum Intent {
    Combat,
    Dialogue { target_npc: Option<String> },
    Exploration,
    Examine,
    Chase,
    Meta,
}

pub struct IntentRoute {
    pub intent: Intent,
    pub agent: AgentKind,       // enum, not string
    pub confidence: f64,        // 0.0-1.0
    pub reasoning: String,
}
```

Python's `Intent` is a string enum with an `agents: list[str]` field. Rust maps intent
directly to `AgentKind` — the enum variant determines the agent, not a string lookup.

**Intent classification follows the same priority chain as Python:**

```rust
impl IntentRouter {
    pub fn classify(&self, input: &str, state: &GameState) -> IntentRoute {
        // 1. Tell/say pattern (regex)
        if let Some(npc) = self.match_tell_pattern(input) {
            return IntentRoute { intent: Intent::Dialogue { target_npc: Some(npc) }, .. };
        }
        // 2. In chase? → Chase
        if state.chase.in_chase { return IntentRoute { intent: Intent::Chase, .. }; }
        // 3. In combat? → Combat
        if state.combat.in_combat { return IntentRoute { intent: Intent::Combat, .. }; }
        // 4. Keyword matching (compiled regex set)
        if let Some(route) = self.match_keywords(input) { return route; }
        // 5. LLM fallback (optional, uses ClaudeClient with haiku model)
        if self.llm_enabled {
            if let Ok(route) = self.classify_with_llm(input, state) { return route; }
        }
        // 6. Default: Exploration → Narrator
        IntentRoute { intent: Intent::Exploration, agent: AgentKind::Narrator, confidence: 0.3, .. }
    }
}
```

**Key difference:** Python mutates game state inside the router (setting `combat.in_combat = True`
when it sees combat keywords). Rust's router is pure — it returns a classification without
side effects. The orchestrator decides whether to start combat based on the route.

### Turn Pipeline Steps

The orchestrator processes a turn in explicit, ordered phases:

```rust
impl Orchestrator {
    pub async fn process_turn(
        &mut self,
        input: &str,
        player_id: &PlayerId,
    ) -> Result<TurnResult, OrchestrationError> {
        // 1. SANITIZE (already done at protocol layer, but defense in depth)
        let clean_input = sanitize_player_text(input);

        // 2. ROUTE
        let route = self.intent_router.classify(&clean_input, &self.state);

        // 3. COMPOSE SYSTEM PROMPT
        let system_prompt = self.prompt_composer.compose(
            route.agent,
            &self.state,
            &self.genre_pack,
        );

        // 4. BUILD CONTEXT
        let context = self.build_agent_context(route.agent, &clean_input);

        // 5. CALL AGENT (streaming)
        let response = self.call_agent(route.agent, &system_prompt, &context).await?;

        // 6. EXTRACT PATCHES (if combat/chase agent)
        let (narration, patches) = self.extract_patches(route.agent, &response)?;

        // 7. APPLY PATCHES
        let pre_state = self.state.snapshot_for_delta();
        self.apply_patches(&patches)?;

        // 8. BACKGROUND: world state agent + trope tick + save
        self.post_turn_update(&clean_input, &narration).await?;

        // 9. COMPUTE DELTA
        let delta = self.state.compute_delta(&pre_state);

        // 10. RETURN
        Ok(TurnResult {
            narration,
            narration_chunks: vec![],  // populated during streaming variant
            state_delta: delta,
            combat_events: patches.combat_events(),
            is_degraded: false,
        })
    }
}
```

Each step has a clear input and output. No step mutates state except step 7 (apply patches)
and step 8 (post-turn update). The pipeline is auditable.

### Agent Context Building

Python's `_build_agent_context()` builds a formatted string with game state. Rust builds
structured sections that the prompt composer assembles:

```rust
fn build_agent_context(&self, agent: AgentKind, input: &str) -> AgentContext {
    let mut ctx = AgentContext::new(input);

    // Common context for all agents
    ctx.add_location(&self.state.location, &self.state.atmosphere);
    ctx.add_active_character(&self.active_character());
    ctx.add_party_status(&self.state.characters);

    // Agent-specific context
    match agent {
        AgentKind::Narrator => {
            ctx.add_npc_registry(&self.state.npc_registry);
            ctx.add_quest_log(&self.state.quest_log);
            ctx.add_active_tropes(&self.state.active_tropes);
            ctx.add_brevity_mandate();  // "3-5 sentences max"
        }
        AgentKind::CreatureSmith => {
            ctx.add_combat_state(&self.state.combat);
        }
        AgentKind::Ensemble => {
            ctx.add_npc_details(target_npc);
        }
        AgentKind::Dialectician => {
            ctx.add_chase_state(&self.state.chase);
        }
        AgentKind::WorldBuilder => {
            ctx.add_full_state_json(&self.state);
            ctx.add_cartography(&self.state);
        }
        _ => {}
    }
    ctx
}
```

**Type-system win:** The `match` on `AgentKind` is exhaustive. If we add a new agent, the
compiler forces us to decide what context it gets. Python's `if agent_name == "narrator":`
silently does nothing for unknown agent names.

### Streaming Response

Python streams via `async for chunk in orchestrator.handle_player_input_streaming(...)`.
Rust uses a `tokio::sync::mpsc` channel:

```rust
pub async fn process_turn_streaming(
    &mut self,
    input: &str,
    player_id: &PlayerId,
    chunk_tx: mpsc::Sender<String>,
) -> Result<TurnResult, OrchestrationError> {
    // ... same pipeline, but step 5 sends chunks through chunk_tx
    // Server reads from chunk_rx and sends NARRATION_CHUNK messages
    // After stream ends, proceed with patch extraction and state update
}
```

The server spawns the orchestrator on one task and reads chunks on another. This way
NARRATION_CHUNK messages go to the client as fast as the agent produces them.

### Post-Turn State Update

After the primary agent responds, the world state agent runs in the background to produce
state patches:

```rust
async fn post_turn_update(&mut self, input: &str, narration: &str) -> Result<(), OrchestrationError> {
    // 1. Call WorldBuilder agent with current state + input + narration
    let world_response = self.call_agent(
        AgentKind::WorldBuilder,
        &self.compose_world_state_prompt(),
        &format!("Action: {} | Response: {}", input, narration),
    ).await;

    // 2. Extract and apply world state patch (with graceful degradation)
    if let Ok(response) = world_response {
        if let Some(patch) = extract_json::<WorldStatePatch>(&response) {
            self.state.apply_world_patch(&patch);
        }
    }
    // Failure is logged, not fatal — ADR-006 graceful degradation

    // 3. Tick tropes (story 2-8 adds the full implementation)
    // 4. Save state (story 2-4 provides SessionStore)
    self.store.save(&self.state.snapshot())?;

    Ok(())
}
```

### Graceful Degradation (ADR-006)

Every agent call has a timeout. If an agent times out or fails:
- Log the error
- Set `is_degraded = true` in the result
- Return a fallback narration ("The world seems to pause for a moment...")
- Never crash the turn loop

Python does this with try/except. Rust uses `Result` with a timeout wrapper:

```rust
async fn call_agent_with_timeout(
    &self,
    agent: AgentKind,
    system: &str,
    context: &str,
    timeout: Duration,
) -> Result<String, AgentError> {
    match tokio::time::timeout(timeout, self.call_agent(agent, system, context)).await {
        Ok(Ok(response)) => Ok(response),
        Ok(Err(e)) => Err(e),
        Err(_) => Err(AgentError::Timeout { agent, duration: timeout }),
    }
}
```

## Scope Boundaries

**In scope:**
- `Orchestrator` struct with `process_turn()` and `process_turn_streaming()`
- `IntentRouter` with keyword matching and LLM fallback
- `AgentContext` builder for per-agent context assembly
- `TurnResult` struct with narration, delta, combat events
- World state agent post-turn update
- Graceful degradation (timeout → fallback narration)
- State snapshot and delta computation
- Save after each turn via `SessionStore`

**Out of scope:**
- Slash commands (local in UI, server-side deferred)
- Speculative pre-generation (optimization, not core loop)
- Scenario-specific logic (accusation, belief cues, NPC actions)
- Media pipelines (render, audio, voice — daemon territory)
- Perception rewriter (multiplayer feature)
- Continuity validator (nice-to-have, not core loop)
- Pacing detection (nice-to-have)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Turn completes | PLAYER_ACTION → intent route → agent call → narration returned |
| Intent routing | "I attack the goblin" → Combat intent → CreatureSmith agent |
| Intent fallback | Unknown input → Exploration → Narrator with confidence 0.3 |
| Keyword routing | Combat/chase keywords correctly classified without LLM |
| Streaming | Narration chunks sent to client as agent produces them |
| State delta | Changes to location/characters/quests included in NARRATION_END |
| World state update | WorldBuilder agent called after turn, patches applied |
| Combat patch | CreatureSmith response with JSON block → patch extracted, applied |
| Graceful degradation | Agent timeout → fallback narration, is_degraded flag set |
| Auto-save | State saved to SessionStore after every turn |
| No side effects in router | IntentRouter.classify() returns route without mutating state |

## Type-System Wins Over Python

1. **`TurnResult` is a struct, not a string.** The server knows exactly what to broadcast without parsing.
2. **`Intent` enum with associated data.** `Dialogue { target_npc }` vs `Intent.DIALOGUE` + separate `target_npc` field.
3. **`AgentKind` enum replaces string keys.** No more `sessions["narrator"]` with potential KeyError.
4. **Exhaustive context building.** New agent kind → compiler forces you to add its context.
5. **Pure intent routing.** Classify returns data, doesn't mutate game state. Combat start is an explicit orchestrator decision.
6. **`Result` for every fallible step.** No silent exception swallowing — degradation is an explicit code path.
