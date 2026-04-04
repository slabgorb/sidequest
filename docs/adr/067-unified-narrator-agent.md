# ADR-067: Unified Narrator Agent — Collapse Multi-Agent into Single Persistent Session

## Status
Accepted

## Context

### The Latency Problem

Playtest session 2 (2026-04-04) measured turn latency at 20-30s despite the
validate_continuity reorder from ADR-066. The remaining bottleneck:

| Phase | Duration | Notes |
|-------|----------|-------|
| Intent classification (Sonnet) | 8-17s | Separate subprocess call |
| Narrator response (Opus) | 10-18s | Persistent session, cached |
| Post-narration (state mutations) | <1s | Already reordered |
| **Total** | **~25s** | |

Intent classification alone accounts for 30-50% of turn latency. It exists to
route player input to one of four agents:

| Intent | Agent | Frequency |
|--------|-------|-----------|
| Exploration, Examine, Meta, Backstory, Accusation | narrator | ~80% of turns |
| Dialogue | ensemble | ~10% |
| Combat | creature_smith | ~5% |
| Chase | dialectician | ~5% |

The narrator handles the vast majority of turns. The three specialist agents
(ensemble, dialectician, creature_smith) are each a separate `claude -p`
subprocess with a different system prompt — they don't share the narrator's
persistent session or its accumulated context.

### What the Specialist Agents Actually Do

All four agents use the same `define_agent!` macro — same transport, same
response parsing, same tool support. They differ only in system prompt:

- **creature_smith**: Combat narration with mechanical resolution hints
- **dialectician**: Chase narration with pursuit/escape mechanics
- **ensemble**: Multi-NPC dialogue with distinct voice management

These are prompt concerns, not architectural ones. The narrator with ADR-059
tool calls can invoke `resolve_combat()`, `resolve_chase()`, etc. for the
mechanical side. The narration itself — describing combat, chase, dialogue —
is something the narrator already does when intent classification is ambiguous
or when Haiku is unavailable.

### Why Separate Agents Existed

The multi-agent architecture (ADR-010) was designed when:

1. The narrator was a stateless one-shot call — no persistent session
2. System prompts were monolithic — cramming combat + chase + dialogue rules
   into one prompt degraded quality
3. Intent classification was cheap (Haiku, <1s) — the routing overhead was
   negligible

All three conditions have changed:

1. ADR-066 established persistent Opus sessions with 1M context
2. ADR-059 tool calls let the narrator invoke specialist behavior on demand
3. Sonnet classification now costs 8-17s per turn (CLI subprocess overhead)

### The Zork Problem Applies to Classification Too

ADR-010's original keyword-based intent routing was replaced with LLM
classification precisely because natural language defeats pattern matching
("I pretend to take the item" ≠ acquisition, "I grab my backpack" ≠ combat).

But the Opus narrator with full conversation context is strictly better at
intent resolution than a stateless Sonnet call with a summary prompt. The
narrator has seen every previous turn, knows the NPCs in the scene, knows
the player's style. Sonnet is classifying from a lossy context summary.

## Decision

### 1. Collapse all agents into the narrator's persistent session

The narrator handles all intents. No separate agents, no intent classification
subprocess, no routing.

```
Before:  Player → Sonnet classify (8-17s) → Agent dispatch → Opus/Sonnet response
After:   Player → Opus narrator (persistent session, cached context)
```

### 2. Specialist behavior via prompt sections and tools

Combat, chase, and dialogue rules become conditional prompt sections injected
based on game state (not LLM-classified intent):

```rust
// State-based prompt injection (zero LLM cost)
if ctx.in_combat {
    prompt.add_section("combat_rules", &genre.combat_rules);
}
if ctx.in_chase {
    prompt.add_section("chase_rules", &genre.chase_rules);
}
if !ctx.npcs_in_scene.is_empty() {
    prompt.add_section("npc_voices", &format_npc_context(ctx));
}
```

The narrator uses ADR-059 tool calls for mechanical resolution:
- `resolve_combat(attacker, target, action)` — returns damage, HP changes
- `resolve_chase(action, terrain)` — returns distance changes, obstacles
- `resolve_dialogue(npc, disposition)` — returns NPC reaction modifiers

### 3. Intent is inferred, not classified

The narrator's response implicitly contains intent information. Post-narration
extraction (already existing for inventory, location, NPC detection) extracts
the action type from the response for OTEL logging and state machine transitions:

```rust
// Post-narration extraction (runs after response is sent to client)
let action_type = extract_action_type(&narration); // Combat, Chase, Dialogue, etc.
emit_otel_span("turn.action_type", action_type);
```

This is the same pattern as location extraction and NPC detection — deferred,
non-blocking, for observability only.

### 4. State machine transitions replace intent routing

Combat and chase entry/exit become state machine transitions triggered by
tool calls or narrator signals, not by pre-classifying player input:

| Trigger | State Change | Source |
|---------|-------------|--------|
| Narrator calls `initiate_combat` tool | → in_combat | Tool call |
| Combat HP reaches 0 or flee succeeds | → out of combat | State mutation |
| Narrator calls `initiate_chase` tool | → in_chase | Tool call |
| Chase resolved or escaped | → out of chase | State mutation |

The existing state overrides in IntentRouter (lines 378-397) already bypass
classification when `in_combat` or `in_chase`. This decision makes that the
*only* path — there is no classification, only state.

## Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Turn latency | 20-30s | 10-18s | -8-17s (classification eliminated) |
| LLM calls per turn | 2-3 | 1 | -50-66% |
| Context quality | Lossy summary for classifier | Full conversation history | Better classification |
| Code complexity | 4 agent definitions, router, classifier | 1 narrator, state machine | Simpler |

## Consequences

### Positive
- Turn latency drops to LLM response time only (~10-15s)
- Narrator has full context for every type of action
- No more misrouting (ensemble handling a combat action, etc.)
- Simpler codebase — remove IntentRouter, HaikuClassifier, 3 agent definitions

### Negative
- System prompt for narrator grows (absorbs combat/chase/dialogue rules)
- No specialist prompt optimization per action type
- Harder to A/B test individual agent behaviors

### Mitigated
- Prompt growth: 1M context window makes this negligible
- Specialist optimization: Opus with full context outperforms Sonnet specialists
  with lossy context — quality improves despite less focused prompts

## Migration Path

### Phase 1: Bypass classification (immediate win)
Route all intents to narrator. Keep IntentRouter code but set it to always
return `narrator`. Measures latency improvement without code removal.

### Phase 2: Absorb specialist prompts
Move combat, chase, and dialogue rules into conditional narrator prompt
sections. Verify narration quality matches or exceeds specialist agents.

### Phase 3: Remove dead code
Delete IntentRouter, HaikuClassifier, creature_smith, dialectician, ensemble
agent definitions. Clean up orchestrator dispatch.

## References

- ADR-010: Intent-based agent routing (superseded by this ADR)
- ADR-032: Haiku classifier with narrator ambiguity resolution (superseded)
- ADR-059: Server-invoked tool calls
- ADR-066: Persistent Opus narrator sessions
