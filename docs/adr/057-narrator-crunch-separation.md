# ADR-057: Narrator Crunch Separation — LLM Narrates, Scripts Crunch

**Status:** Partially superseded by [ADR-059](059-monster-manual-server-side-pregen.md) (narrator tool-calling removed; crunch separation principle retained via sidecar tools)
**Date:** 2026-04-02
**Deciders:** Keith
**Relates to:** ADR-056 (Script Tool Generators), ADR-001 (Claude CLI Only), ADR-031 (Game Watcher Telemetry)

## Context

The narrator currently performs three jobs simultaneously:

1. **Narration** — creative prose, dialogue, scene-setting
2. **Intent interpretation** — deciding what happened ("did the player acquire that item or just look at it?")
3. **Crunch** — emitting a ~12-field JSON block with exact schemas for footnotes, items, NPCs, quests, visual scenes, mood, personality events, resource deltas, action rewrites, and flags

Job 3 is the problem. The system prompt spends ~1,580 tokens (63% of the narrator identity) documenting JSON schemas. Every turn, the LLM must simultaneously write prose AND serialize structured data — a dual-task penalty that produces malformed JSON, missing fields, and hallucinated values. We then run a 3-tier extraction strategy to recover from the failures.

This is backwards. The LLM is excellent at jobs 1 and 2. It is mediocre at job 3. And job 3 is deterministic — given the narrator's intent signals, a script can produce the structured output perfectly every time.

### The Principle

> **Narration → LLM. Intent → LLM. Crunch → Scripts.**

"Crunch" includes:
- Mechanical state mutations (HP, inventory, quest state)
- Structured data formatting (JSON emission, schema compliance)
- Lookups against game state (merchant inventories, loot tables, stat blocks)
- Format-sensitive extraction (footnote structuring, visual scene decomposition)

"Meta-crunch" — asking the LLM to get JSON formatting perfect — is still crunch. The work is mechanical even though the artifact looks like text.

### What ADR-056 Covers vs What This ADR Covers

ADR-056 introduced script tool *generators* — Rust binaries that create new game objects (NPCs, encounters, items) from genre pack data. The narrator calls them when it decides to introduce something new.

This ADR goes further: **eliminate the narrator JSON block entirely.** Every field currently in the fenced JSON output becomes either a tool call or unnecessary.

## Decision

Replace the narrator's monolithic JSON output block with a two-phase tool call architecture. The narrator's only direct output is prose.

### Two-Phase Turn Architecture

**Phase 1 — During Narration:** The LLM calls tools as it generates prose. When it
decides to introduce an NPC, it calls `namegen` with the parameters in its head
(role, culture, context). When a player acquires an item, it calls `item_acquire`.
Each tool returns a JSON block that the LLM can reference in its prose (using the
generated name, referencing the item description, etc.).

**Phase 2 — After Narration:** A single `assemble_turn` script collects all tool
call results from the turn, plus the prose output, and assembles them into the
`ActionResult` struct the server already expects. The server never parses narrator
prose for structured data — it reads the assembled turn package.

```
┌─────────────────────────────────────────────────┐
│ claude -p --allowedTools Bash(tool1,tool2,...)   │
│                                                   │
│  LLM generates prose                              │
│    ├── calls namegen → gets NPC JSON              │
│    ├── calls item_acquire → gets item JSON        │
│    ├── calls set_mood("tension") → ack            │
│    └── writes prose referencing tool results       │
│                                                   │
│  Final output: prose only                         │
└──────────────────────┬────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│ assemble_turn                                     │
│                                                   │
│  Inputs:                                          │
│    - narrator prose (the only LLM output)         │
│    - tool call log (all JSON blocks from phase 1) │
│                                                   │
│  Output:                                          │
│    - ActionResult struct (typed, validated)        │
│                                                   │
│  The 3-tier extraction pipeline (extractor.rs)    │
│  is eliminated. No regex. No JSON recovery.       │
└─────────────────────────────────────────────────┘
```

This means:
- The LLM never emits a fenced JSON block
- The extraction pipeline (`extractor.rs`) goes away
- Every mechanical action is a typed tool call visible in OTEL
- `assemble_turn` is deterministic — it just collects and validates

### Tool Catalog (replacing JSON fields)

| Current JSON field | Replacement | Who decides | Who formats |
|-------------------|-------------|-------------|-------------|
| `footnotes` | `lore_mark` tool — narrator places `[N]` in prose, calls tool with summary + category | LLM decides what's notable | Script structures it |
| `items_gained` | `item_acquire` tool — narrator signals acquisition intent | LLM decides "player picked it up" | Script resolves from inventory/genre data |
| `npcs_present` | Already moving to `namegen` (ADR-056) for new NPCs. Recurring NPCs: `npc_present` tool | LLM decides who's in scene | Script provides canonical identity |
| `quest_updates` | `quest_update` tool — narrator signals state change | LLM interprets what happened | Script transitions quest state machine |
| `visual_scene` | `scene_render` tool — narrator calls with subject description | LLM describes what to paint | Script formats tier/mood/tags |
| `scene_mood` | `set_mood` tool — single string arg | LLM feels the mood | Script validates against enum |
| `scene_intent` | `set_intent` tool — single string arg | LLM classifies next action | Script validates against enum |
| `personality_events` | `personality_event` tool — narrator signals significant moment | LLM detects significance | Script structures event type |
| `resource_deltas` | `resource_change` tool — narrator signals spend/gain | LLM interprets resource use | Script validates against declarations |
| `merchant_transactions` | `merchant_transact` tool — narrator signals buy/sell | LLM detects commerce | Script resolves pricing/inventory |
| `sfx_triggers` | `play_sfx` tool — narrator picks sound | LLM matches action to sound | Script validates against library |
| `action_rewrite` | `rewrite_action` preprocessor — runs BEFORE narration | N/A — mechanical transform | Script rewrites to you/named/intent |
| `action_flags` | `classify_action` preprocessor — runs BEFORE narration | N/A — mechanical classification | Script classifies booleans |
| **(all of the above)** | `assemble_turn` — post-narration assembler | N/A | Collects all tool call results + prose into `ActionResult` |

### What the Narrator Prompt Becomes

Before (~2,500 tokens):
- Identity + pacing + agency + constraint handling (~400 tokens)
- JSON schema documentation for 12+ fields (~1,580 tokens)
- Example JSON block (~200 tokens)
- Protocol rules per field type (~300 tokens)

After (~600 tokens):
- Identity + pacing + agency + constraint handling (~400 tokens)
- "Here are your tools" — one line per tool (~200 tokens)

The 75% reduction in system prompt tokens is not the primary benefit — it's the elimination of the dual-task penalty and the deterministic OTEL coverage.

### Preprocessors vs Reactive Tools

Two categories:

**Preprocessors** run BEFORE the narrator sees the action:
- `rewrite_action` — produces you/named/intent rewrites (already partially implemented)
- `classify_action` — produces boolean flags (references_npc, references_inventory, etc.)

These don't need LLM judgment. They're mechanical transforms on the player's input. Moving them out of the narrator's output means the narrator never has to emit `action_rewrite` or `action_flags`.

**Reactive tools** are called BY the narrator during generation:
- Everything else in the table above
- The narrator decides *when* to call them based on what's happening in the story
- The tools return structured data that the server captures

### OTEL Implications

This is a massive win for observability. Currently, "did the narrator engage the inventory system?" requires parsing a JSON block that may be malformed. With tool calls, every mechanical action is a discrete subprocess invocation visible in OTEL spans. The GM panel shows exactly which tools fired, with what arguments, and what they returned. No more guessing whether Claude improvised combat damage or actually called the HP system.

### Migration Path

This is not a flag day. Fields migrate incrementally. The `assemble_turn` script is
built in Phase 1 and grows to consume each new tool's output as it comes online.

1. **Phase 1: Infrastructure.** Build `assemble_turn` script. Move `action_rewrite` and `action_flags` to preprocessors (no narrator involvement needed). `assemble_turn` initially just passes through the existing JSON block + preprocessor results.
2. **Phase 2: Simple enums.** Move `scene_mood` and `scene_intent` to simple tool calls (single string arg each). `assemble_turn` merges them into the ActionResult.
3. **Phase 3: Inventory.** Move `items_gained` and `merchant_transactions` to `item_acquire` / `merchant_transact` tools. Remove item/merchant schema docs from narrator prompt.
4. **Phase 4: Lore.** Move `footnotes` to `lore_mark` tool. Narrator still places `[N]` markers in prose — tool structures the metadata.
5. **Phase 5: Visual.** Move `visual_scene` to `scene_render` tool. Narrator calls with a subject description, tool formats tier/mood/tags.
6. **Phase 6: Quests.** Move `quest_updates` to `quest_update` tool.
7. **Phase 7: Remaining.** Move `personality_events`, `resource_deltas`, `sfx_triggers` to tools.
8. **Phase 8: Eliminate JSON block.** Remove fenced JSON output from narrator prompt entirely. `assemble_turn` is now the sole producer of `ActionResult`. Delete `extractor.rs` and the 3-tier extraction pipeline.

Each phase removes fields from the JSON block AND the corresponding schema
documentation from the system prompt. The narrator prompt shrinks with each phase.
`assemble_turn` grows to replace `extractor.rs` — but it's deterministic assembly
from typed tool outputs, not regex recovery from free-form text.

## Consequences

### Positive

- **Narrator does what it's best at.** Creative prose and intent interpretation, not JSON formatting.
- **Deterministic mechanical output.** Tool calls return typed, validated data. No more malformed JSON recovery.
- **75% smaller narrator prompt.** ~1,900 tokens of schema docs eliminated.
- **Full OTEL coverage.** Every mechanical action is a visible tool invocation. The GM panel becomes a complete audit trail.
- **No more LLM compensation.** If a tool doesn't fire, the mechanical action didn't happen. Claude can't silently improvise combat or inventory changes — there's no JSON field to fake it in.

### Negative

- **More tool calls per turn.** A typical turn might invoke 3-5 tools (mood, intent, visual, maybe an item or NPC). Each is a subprocess. Mitigated: these are lightweight Rust binaries, not LLM calls.
- **Migration complexity.** 8-phase incremental migration touching narrator prompt, extraction pipeline, and server dispatch. Mitigated: each phase is independently shippable and testable.
- **Tool call ordering.** Some tools depend on narrator output (e.g., `lore_mark` needs the prose to exist first). The `claude -p --allowedTools` mechanism handles this — Claude calls tools during generation, interleaved with prose.

### Neutral

- **ADR-056 generators are complementary.** Entity generators (namegen, encountergen) create new objects. This ADR's tools handle mechanical extraction from narrator output. Both use the same `--allowedTools Bash` mechanism.

## Alternatives Considered

### Keep JSON Block, Improve Extraction
Status quo with better parsing. Doesn't solve the dual-task penalty, prompt bloat, or OTEL blind spots. The fundamental problem is architectural, not implementational.

### Structured Output via Claude API
Would require switching from CLI to SDK (violates ADR-001). Also doesn't solve the dual-task penalty — the LLM still has to decide field values alongside prose.

### Post-hoc Extraction LLM
Run a second, cheaper LLM call to extract structured data from the narrator's prose. Doubles latency, adds cost, and the extraction LLM has the same failure modes. Worse in every dimension.
