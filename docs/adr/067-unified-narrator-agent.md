---
id: 67
title: "Unified Narrator Agent — Collapse Multi-Agent into Single Narrator"
status: accepted
date: 2026-04-04
deciders: [Keith Avery]
supersedes: [10]
superseded-by: null
related: [98]
tags: [agent-system, narrator, narrator-migration]
implementation-status: live
implementation-pointer: null
---

# ADR-067: Unified Narrator Agent — Collapse Multi-Agent into Single Narrator

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

1. ADR-066 established Opus as the narrator model (ADR-098 later made turns stateless)
2. ADR-059 tool calls let the narrator invoke specialist behavior on demand
3. Sonnet classification now costs 8-17s per turn (CLI subprocess overhead)

### The Zork Problem Applies to Classification Too

ADR-010's original keyword-based intent routing was replaced with LLM
classification precisely because natural language defeats pattern matching
("I pretend to take the item" ≠ acquisition, "I grab my backpack" ≠ combat).

But the Opus narrator with full per-turn ground truth is strictly better at
intent resolution than a stateless Sonnet call with a summary prompt. The
narrator receives the complete re-injected world state on every turn — NPCs,
party peers, game context, player history — while Sonnet is classifying from
a lossy context summary.

## Decision

### 1. Collapse all agents into the narrator

The narrator handles all intents. No separate agents, no intent classification
subprocess, no routing.

```
Before:  Player → Sonnet classify (8-17s) → Agent dispatch → Opus/Sonnet response
After:   Player → Opus narrator (each turn is a fresh claude -p call)
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
- Prompt growth: bounded per-turn prompts (ADR-098) keep system prompt size stable
- Specialist optimization: Opus outperforms Sonnet specialists with lossy context —
  quality improves despite less focused prompts

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
- ADR-066: Persistent Opus narrator sessions (superseded by ADR-098)
- ADR-098: Stateless Narrator Turns — Drop --resume, Bounded Per-Turn Prompts

## Post-ADR-098 Note (2026-05-10)

ADR-098 superseded the persistent-session model from ADR-066. The unified-agent
decision in this ADR (one narrator handles all intents) remains in force; the
references above to "persistent session" and "cached context" describe the original
ADR-066 mechanism and are preserved for historical context. As of ADR-098, each
narrator turn is a fresh `claude -p` call — no `--resume`, no session-id, no
accumulated session history.

## Post-Spec-2026-05-20 Note: Intent inference site wired

ADR-067 promised inference rather than pre-narration classification:
the narrator's response implicitly carries intent information, and
post-narration extraction lifts the action type for OTEL telemetry and
state-machine transitions. That inference site was never built — until
the 2026-05-20 confrontation-intent-validator spec.

Spec: `docs/superpowers/specs/2026-05-20-confrontation-intent-validator-design.md`
Plan: `docs/superpowers/plans/2026-05-20-confrontation-intent-validator.md`

Driver bug: 2026-05-20 dust_and_lead playtest. A five-turn negotiation
over a horse (the Bonita / saddle / eight-dollars scene) played as
freeform fiction with zero `confrontation.*` OTEL spans because the
narrator never emitted `confrontation=negotiation` and the legacy
prose-regex lie-detector only covered combat and chase phrases.

### What this delivers

1. **The inference site is `sidequest.agents.confrontation_intent_validator.validate(...)`.**
   The validator reads `ActionRewrite.intent` (formerly dead
   infrastructure that the narrator emitted but no downstream consumer
   read) and compares it to the narrator's declared `confrontation`
   field against per-confrontation vocabulary owned by each
   `ConfrontationDef` in `rules.yaml`.

2. **`TurnRecord.classified_intent` is populated from real signal.**
   On the happy path it carries `action_rewrite.intent` verbatim; on a
   mismatch it carries the validator's `ValidationResult.matched_type`;
   when the narrator omits `action_rewrite.intent` entirely it is
   `"unspecified"`. The hardcoded `"unknown"` stub at
   `sidequest/server/websocket_session_handler.py` is removed; a grep
   guard test pins the literal dead.

3. **The legacy prose-regex lie-detector is retired in the same change.**
   `_CONFRONTATION_TRIGGER_PATTERNS` and
   `_scan_for_confrontation_trigger_keywords` in
   `sidequest/server/narration_apply.py` are deleted; the
   `state_transition field=confrontation op=skipped_with_trigger_keywords`
   watcher event is gone. One mechanism per problem
   (`memory/feedback_one_mechanism_per_problem.md`).

4. **Per-confrontation-def dispatch policy.** Each `ConfrontationDef`
   declares `on_intent_mismatch: warn | soft_suggest | reprompt`.
   Lethal / genre-truth heavy types (combat, ship_combat, dogfight,
   chase, standoff) default to `reprompt`; social-pressure /
   transactional types (negotiation, poker, trial, auction,
   social_duel, scandal) default to `warn`. `tea_and_murder` uses
   `warn` for every type per the cosy-genre pacing rule.

5. **One-iteration reprompt loop.** When severity is `reprompt`, the
   orchestrator re-invokes `run_narration_turn` exactly once with an
   `extra_directive` injected into the recency zone. Bounded to one
   retry; on second-narrator failure the first attempt's narration is
   applied and a `confrontation.intent_mismatch_reprompt_failed` span
   fires.

6. **New OTEL spans.** Three new spans on the `confrontation`
   component: `confrontation.intent_mismatch`,
   `confrontation.intent_mismatch_resolved`, and
   `confrontation.intent_mismatch_reprompt_failed`. The GM panel
   surfaces all three via the existing generic state_transition
   routing — no panel-specific UI change needed.

### What does NOT change

- The unified-narrator topology. No specialist agents resurrected from
  ADR-010. No pre-narration intent classifier (ADR-067 killed that
  with cause — 8-17s latency hit).
- The narrator's prompt assembly. The `CONFRONTATION_TRIGGER_CONSTRAINT`
  prompt-guardrail text in
  `sidequest/agents/narrator_guardrails.py` and its Recency-zone
  registration both stay — that's prompt steering (prevent the
  narrator from forgetting `confrontation` in the first place), a
  different mechanism than the deleted prose-regex scanner.
- The narrator's tool-use output contract. The narrator already
  emitted `action_rewrite.intent` per
  `sidequest/agents/narrator_prompts/output_only_sdk.md`; this work
  just wires the first downstream consumer.

### Replay regression

`sidequest-server/tests/server/test_dust_and_lead_horse_replay.py`
pins the fix against the real `spaghetti_western` pack. Six
parametrized intent strings derived from the dust_and_lead save's
horse-purchase narration each fire
`confrontation.intent_mismatch matched_type=negotiation severity=warn`.
The save file itself predates the validator (its NARRATION events
carry prose but no `action_rewrite.intent`), so the intent strings are
hand-derived from the prose with per-turn seq annotations for
traceability.
