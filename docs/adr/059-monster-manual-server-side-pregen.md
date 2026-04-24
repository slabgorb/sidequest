---
id: 59
title: "Monster Manual — Server-Side Pre-Generation via Game-State Injection"
status: accepted
date: 2026-04-03
deciders: [Keith]
supersedes: [56]
superseded-by: null
related: [1, 3, 7, 20]
tags: [code-generation, agent-system]
implementation-status: drift
implementation-pointer: 87
---

# ADR-059: Monster Manual — Server-Side Pre-Generation via Game-State Injection

## Context

ADR-056 introduced Rust tool binaries (namegen, encountergen, loadoutgen) that the
narrator would call via `claude -p --allowedTools Bash(...)`. After 6+ iterations
(prompt zones, wrapper scripts, env vars, mandatory workflows, casting calls, XML
audition tags), Claude (Sonnet) in single-prompt print mode consistently ignores
tool-calling instructions and writes prose directly.

**Root cause:** `claude -p` is a prose generation task. Tool calling is an interruption
Claude can skip because it can fulfill the request entirely in prose. No amount of
prompt engineering changes this fundamental incentive — proven empirically across
Primacy, Early, Valley, and Recency attention zones.

**Key discovery:** Claude DOES absorb data from the prompt — proven by umlaut
generation matching conlang corpus patterns. It reads the NPC data and generates
names *in the style of* the pool, but invents rather than selects. The data is
reaching Claude; the constraint framing fails.

## Decision

**Embed pre-generated content directly in `<game_state>` as world facts.**

Claude treats `<game_state>` as ground truth — the authoritative description of
the game world. NPCs listed there are used naturally with correct names, dialogue
quirks, and behavioral traits. Enemies listed there are referenced with exact names,
abilities, and attack patterns.

No special XML sections. No meta-instructions. No casting calls. World data in the
world data section.

### The Monster Manual

A persistent JSON file at `~/.sidequest/manuals/{genre}_{world}.json` containing
pre-generated NPCs and encounter blocks. Full stat blocks stored, indexed by
compound key `(name, faction, world)`.

Seeded on first session start by calling tool binaries server-side for each faction
in the genre pack. Grows over play sessions — every generated entry persists.

### Game-State Injection (the validated pattern)

The Monster Manual's formatting methods append to the `state_summary` string that
becomes the `<game_state>` prompt section:

```
NPCs nearby (not yet met by player):
  - Joch Glowvein (wasteland trader, Scrapborn) — blunt, quotes prices in three barter systems
  - Seven Jewsa (village elder, Vaultborn) — reserved, pauses mid-sentence as if buffering

Hostile creatures in the area:
  - Salt Burrower (tier 2, HP 14) — eyeless ambush predator, chitin mandibles
    Abilities: Burrow Ambush, Mandible Crush. Weakness: bright light, fire.
```

The prompt stays lean (~100-200 extra tokens). Full mechanical data (OCEAN profiles,
stat ranges, trope connections) stays in the Manual backend, never in the prompt.

### Two-Tier Data Flow

1. **Prompt** gets names + roles + brief personality/speech quirks
2. **Post-narration gate** matches used names against Manual via compound key lookup
3. **NPC registry** enriched with full stat block from Manual — same gate, same OTEL

### Compound Key

`(name, faction, world)` — because the same name could exist in different factions
or worlds. Lookup is a hash map operation, not string matching on prose.

### Entry Schema

Each entry carries tags for future filtering even if filtering isn't implemented yet:

```rust
pub struct ManualNpc {
    pub data: serde_json::Value,     // full namegen output
    pub name: String,
    pub role: String,
    pub culture: String,
    pub location_tags: Vec<String>,  // biome/terrain for future filtering
    pub state: EntryState,           // Available, Active, Dormant
}
```

### Lifecycle

- **Available** — pre-generated, not yet used in narration
- **Active** — narrator introduced them, in current scene
- **Dormant** — used previously, can return

Transitions: session start seeds → narrator uses name → mark Active → location
change → mark Dormant → seed new batch.

### Bottle Episode Compatibility

Bottle episodes (fixed NPC cast for a scene/quest) use the same pattern. The cast
list IS the "NPCs nearby" section. The Manual serves both open-world exploration
and tightly scripted scenarios.

### What Gets Removed

- `--allowedTools Bash` from Claude CLI invocations
- All tool prompt sections (`<tool_workflow>`, `<casting_call>`, `<on_set>`, `<available_characters>`)
- Sidecar JSONL mechanism (tool_call_parser, sidecar env vars)
- `script_tools` HashMap on Orchestrator
- `register_script_tool()` and wrapper script infrastructure

### What Stays

- Tool binaries (namegen, encountergen, loadoutgen) — called by server, not Claude
- Post-narration NPC gate — validates names, enriches from Manual
- Binary path discovery — paths move to AppState

## Empirical Validation

Tested via `scripts/preview-prompt.py --test` against `claude -p`:

| Approach | Zone | Result |
|----------|------|--------|
| `<tool_workflow>` mandatory steps | Primacy | Zero tool calls across 30+ turns |
| `<available_characters>` list | Early | Claude invents names, ignores list |
| `<casting_call>` audition XML | Early | Claude absorbs style (umlauts!), still invents |
| `<on_set>` actors-on-set framing | Recency | Claude invents, absorbs style |
| **`<game_state>` "NPCs nearby"** | **Valley** | **Claude uses exact names + dialogue quirks + behavior** |
| **`<game_state>` "Hostile creatures"** | **Valley** | **Claude uses exact enemy names + abilities** |

The winning approach places data in the lowest-attention zone. The key is not
attention priority — it's **framing**. Claude treats `<game_state>` as world truth
and meta-instruction sections as advisory.

## Consequences

### Positive

- **Reliable.** Claude uses game_state NPCs naturally — validated empirically.
- **No special framing.** No XML tags, no meta-instructions. Just world facts.
- **Persistent.** Monster Manual grows over sessions. Rich worlds accumulate.
- **Prompt-efficient.** ~100-200 tokens for the pool section.
- **Compatible.** Works with bottle episodes, open-world, multiplayer.
- **Deterministic lookup.** Compound key → full stat block. No string matching.
- **GM prep metaphor.** Pre-roll NPCs before session, pull from deck during play.

### Negative

- **Speculative generation.** Some entries may never be used. Cost: ~50-100ms per
  binary call, negligible vs 3-10s Claude calls.
- **Narrator may still invent.** Game_state embedding works reliably but isn't
  deterministic. Post-narration gate catches inventions and falls back to namegen.
- **Disk I/O.** Manual file read/write per session. Small JSON, not a concern.

### Neutral

- Tool binary sidecar JSONL code becomes dead code. Harmless.
- ADR-056's binaries remain the foundation; only the invocation model changes.
- ADR-057's narrator-crunch separation principle is validated but the mechanism
  is game-state injection, not tool calls.

## Alternatives Considered

### A: Narrator calls tools via --allowedTools (Rejected — ADR-056)
Six iterations failed. Fundamental incentive mismatch in `claude -p` mode.

### B: XML casting/audition sections (Rejected)
Claude absorbs style but invents instead of selecting. Proven by umlaut generation
— data reaches Claude, constraint framing fails.

### C: Meta-instruction constraints ("HARD RULE", "MUST NOT invent") (Rejected)
Claude treats these as advisory. Constraint escalation doesn't change behavior.

### D: Game-state embedding (Accepted)
Claude treats `<game_state>` as world truth. Names, abilities, and dialogue quirks
used correctly on first test. The simplest approach that works.
