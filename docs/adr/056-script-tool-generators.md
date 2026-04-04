# ADR-056: Script Tool Generators — Offloading Structured Generation from LLM to Rust Binaries

**Status:** Superseded by [ADR-059](059-monster-manual-server-side-pregen.md)
**Date:** 2026-04-01
**Deciders:** Keith
**Relates to:** ADR-001 (Claude CLI Only), ADR-003 (Genre Pack Architecture), ADR-011 (JSON Patches), ADR-018 (Trope Engine), ADR-057 (Narrator Crunch Separation)

## Context

The narrator currently emits a ~12-field JSON block after every turn (footnotes, items,
NPCs, quests, visual scene, mood, personality events, resource deltas, etc.). The server
parses this with a 3-tier extraction strategy. Every field Claude must generate is a
chance for malformed JSON, missing fields, or hallucinated values with no mechanical
backing.

Two recurring problems:

1. **Claude makes up the same things.** Given similar situations, it produces near-identical
   NPCs, items, locations, and encounters without stirring up randomness. Genre packs
   contain rich data (archetypes, cultures, tropes, power tiers, lore) that could seed
   variety deterministically.

2. **Structured output is hard for LLMs.** Asking Claude to simultaneously narrate AND
   emit a precise JSON schema is a dual-task penalty. Claude is better at deciding
   *when* to introduce a new NPC than at generating the NPC's stat block, OCEAN profile,
   Markov-chain name, and trope connections in valid JSON.

The `sidequest-namegen` binary (merged in OQ-1 PR #236) proved the pattern: a Rust
binary that reads genre pack data, injects randomness, and returns structured JSON.
The narrator calls it via `--allowedTools Bash(sidequest-namegen:*)` during `claude -p`.
The server also calls it server-side to validate NPC registry entries.

## Decision

**Adopt a "script tool" pattern:** Rust binaries that generate structured game objects
from genre pack data, exposed to Claude via `--allowedTools Bash` and optionally
called server-side for validation.

### The Pattern

Every generator follows the same template:

1. **Own crate** in the `sidequest-api` workspace (`crates/sidequest-{name}/`)
2. **CLI binary** — `--genre` and `--genre-packs-path` required, everything else optional
3. **Pulls from genre pack YAML** via the `sidequest-genre` loader (reuses existing
   deserialization — no new parsers)
4. **Injects randomness** via `rand::rng()` — culture selection, stat jitter, template
   selection, Markov chain generation
5. **Returns JSON to stdout** — the exact structure the game engine needs, ready to
   slot into `ActionResult` fields
6. **Exposed via `--allowedTools Bash(binary_path:*)`** to the narrator's `claude -p`
   invocation — Claude calls it when it decides to introduce the thing
7. **Server-side validation optional** — the orchestrator can also call the binary to
   verify/enrich extracted data (as namegen does for NPC registry entries)

### What Claude's Job Becomes

Claude decides the *narrative trigger* — "a monster appears", "the player finds a
weapon", "they arrive at a new location." Then it calls the tool with optional hints
(role, tier, context) and gets back a fully-formed game object. Claude weaves the
result into prose. No JSON emission for that object type.

### Generator Catalog

Ordered by impact (most mechanical state, richest genre pack data, highest hallucination
risk):

| Priority | Generator | Crate | Genre Pack Sources | What It Returns |
|----------|-----------|-------|--------------------|-----------------|
| **Done** | NPC Identity | `sidequest-namegen` | cultures, archetypes, tropes, corpus, visual_style | Name, OCEAN, personality, inventory, trope connections, **visual_prompt** |
| **1** | Encounter/Monster | `sidequest-encountergen` | archetypes, power_tiers, rules, tropes, visual_style | Enemy stat blocks: name, HP, abilities, weaknesses, disposition, **visual_prompt** |
| **2** | Location/POI | `sidequest-placegen` | cartography, lore, cultures, theme, visual_style | Location block: name, description, features, hidden elements, routes, mood, **visual_prompt** |
| **3** | Item | `sidequest-itemgen` | archetypes (inventory), power_tiers, progression, rules | Item: name, description, category, mechanical effects, tier |
| **4** | Madlib Descriptions | `sidequest-descgen` | theme (dinkus, session openers), visual_style, lore | Atmospheric prose fragments for common scene types |
| **5** | Lore Fragment | `sidequest-loregen` | lore, tropes, cultures, factions | Canonical lore fragment consistent with world data |

### Visual Prompt Generation

Generators that produce visible entities (NPCs, monsters, locations) MUST include a
`visual_prompt` field — a concrete, physical-only image description suitable for the
daemon's renderer. The generator builds this from `visual_style.yaml` (genre art
direction, color palettes, style keywords) combined with the entity's physical
attributes (archetype appearance, terrain type, architectural style).

This eliminates the narrator's burden of crafting `visual_scene.subject` for
tool-generated entities. Claude still provides `visual_scene` for narrative moments
that aren't entity introductions (e.g., "the sun sets over the wasteland"), but
entity portraits and location landscapes come pre-prompted from the tool.

### What Stays with Claude

- **Narration prose** — the core creative act
- **Intent interpretation** — deciding what happened, who's present, what changed

All other mechanical output (visual scene, personality events, quest updates, scene
mood/intent, footnotes, resource deltas) migrates to tool calls per ADR-057. Claude
still *decides* when these happen — it just calls a tool instead of emitting JSON.

### Prompt Protocol

Each tool gets a section in the narrator system prompt:

```
[ENCOUNTER TOOL]
When introducing a new enemy or group of enemies, call the encounter generator:
  sidequest-encountergen --genre {genre} --genre-packs-path {path} --tier {power_tier} [--role "ambush predator"] [--count 3]
Use the returned stat blocks as ground truth for the encounter. Do NOT invent
stats, HP, or abilities — the tool output is canonical.
```

Claude sees a tool description, knows the flags, calls it when narratively appropriate.
The tool returns JSON, Claude incorporates it.

## Consequences

### Positive

- **Mechanical grounding.** Every generated game object has real stats backed by genre
  pack data, not Claude improvisation. The GM panel can audit whether the narrator
  respected the generated stats.

- **Variety.** Randomness injection (Markov names, stat jitter, template selection)
  produces different results each time, breaking Claude's repetition patterns.

- **Reduced extraction complexity.** Fields that move to tool calls no longer need
  to be in the narrator's JSON block. Fewer fields = simpler extraction, fewer
  parse failures.

- **Separation of concerns.** Claude handles narrative judgment (when, why, how to
  describe). Rust handles data generation (what, with what stats, from what source).

- **Genre pack investment pays off.** The rich YAML data in genre packs (archetypes,
  cultures, tropes, power tiers, lore, cartography) becomes directly useful at
  runtime, not just as LLM context.

### Negative

- **More crates to maintain.** Each generator is a small binary crate. Mitigated by
  sharing `sidequest-genre` for all deserialization.

- **Tool call latency.** Each `--allowedTools Bash` invocation is a subprocess spawn.
  Mitigated by keeping binaries small and fast (genre pack loading is the only I/O,
  and it's cached).

- **Prompt complexity.** Each tool adds a protocol section to the narrator prompt.
  Mitigated by keeping protocol descriptions short (5-6 lines each) and only
  loading tools relevant to the current genre pack's capabilities.

### Neutral

- **Superseded by ADR-057 for JSON block elimination.** This ADR introduced the tool
  pattern for entity *generation*. ADR-057 extends the same pattern to all mechanical
  extraction — eliminating the narrator JSON block entirely. Fields originally expected
  to stay in the JSON output (visual_scene, scene_mood, quest_updates, footnotes) are
  now migrating to discrete tool calls per ADR-057's phased plan.

## Alternatives Considered

### MCP Tools
Claude Code supports MCP tool servers, but `claude -p` subprocess mode does not.
All narration runs through `claude -p`, so MCP is not an option.

### Structured Output / Tool Use API
Would require switching from Claude CLI to the SDK. ADR-001 commits to CLI-only.
The `--allowedTools Bash` mechanism gives us tool use within that constraint.

### Keep Everything in the JSON Block
Status quo. Works but produces hallucinated stats, repetitive outputs, and a
fragile 12-field extraction pipeline. The namegen experiment proved the tool
pattern is strictly better for mechanical data.

## Implementation Notes

- Start with `sidequest-encountergen` (Priority 1) — combat is the highest-stakes
  mechanical subsystem and the most common source of hallucinated stats.
- Each generator should have integration tests that verify JSON output schema and
  that all genre packs produce valid output.
- Server-side validation is opt-in per generator. Start without it; add when
  playtesting reveals the narrator ignoring tool output.
