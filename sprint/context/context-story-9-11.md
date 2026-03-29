---
parent: context-epic-9.md
---

# Story 9-11: Structured Footnote Output — Narrator Emits NarrationPayload with Footnotes

## Business Context

When the narrator reveals information — a location's history, an NPC's secret, a lore
detail — that revelation should be captured as a structured footnote. The narrator currently
returns plain prose; this story extends the output to include a `footnotes[]` array alongside
the narration. Each footnote represents a discovery or callback to prior knowledge,
enabling the downstream journal system (9-12, 9-13) and enriching the narrator feedback
loop (9-4).

This is the **creation pipeline** for the living journal system. Without structured
footnote output, there's no way to automatically build a quest log from play.

**Depends on:** Story 9-3 (KnownFact model — footnotes create KnownFact entries)

## Technical Approach

### Narrator Output Extension

Extend the narrator's response payload to include structured footnotes alongside prose:

```rust
struct NarrationPayload {
    prose: String,
    footnotes: Vec<Footnote>,
}

struct Footnote {
    marker: u32,                    // [1], [2], etc. — matches superscript in prose
    fact_id: Option<String>,        // links to existing KnownFact if callback
    summary: String,                // "The Corrupted Grove — corruption detected"
    category: FactCategory,         // Lore, Place, Person, Quest, Ability
    is_new: bool,                   // true = new discovery, false = callback
}

enum FactCategory {
    Lore,
    Place,
    Person,
    Quest,
    Ability,
}
```

### Narrator Prompt Instruction

Add a section to the narrator system prompt instructing Claude to emit footnote markers
when revealing or referencing knowledge:

```
[FOOTNOTE PROTOCOL]
When you reveal new information or reference something the party previously learned,
include a numbered marker in your prose like [1], [2], etc.

For each marker, emit a footnote in your structured output with:
- summary: one-sentence description of the fact
- category: one of Lore, Place, Person, Quest, Ability
- is_new: true if this is a new revelation, false if referencing prior knowledge

Example prose: "As you enter the grove, Reva feels a deep wrongness [1]."
Example footnote: { marker: 1, summary: "Corruption detected in the grove's oldest tree", category: "Place", is_new: true }
```

### Orchestrator Parsing

The orchestrator extracts footnotes from the narrator's structured JSON response.
For each `is_new: true` footnote, a new KnownFact is created and persisted to game state.
For `is_new: false` footnotes, the `fact_id` field links to the existing KnownFact.

The `register_knowledge_context()` method (story 9-4) provides the narrator with existing
KnownFacts; this story handles the **output** side — the narrator producing new ones.

### Parallel to Existing Patterns

This follows the established pattern in `sidequest-agents`:
- `register_ability_context()` (9-2) injects context INTO the narrator prompt
- `register_knowledge_context()` (9-4) injects known facts INTO the narrator prompt
- **This story** extracts footnotes FROM the narrator response

The `NarrationPayload` extends the existing `GameMessage::Narration` variant.

## Scope Boundaries

**In scope:**
- `NarrationPayload` and `Footnote` types in `sidequest-protocol`
- Narrator prompt instruction for footnote emission
- Orchestrator parsing of footnote markers from narrator response
- Auto-creation of KnownFact entries from `is_new: true` footnotes
- `FactCategory` enum for footnote classification

**Out of scope:**
- UI rendering of footnotes (that's 9-12)
- Journal browse view (that's 9-13)
- Tiered injection of known facts into prompt (that's 9-4)
- Semantic search or relevance ranking of footnotes
- Narrator training/fine-tuning for footnote quality

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Structured output | Narrator response includes `footnotes[]` array alongside prose |
| Marker parsing | Footnote markers `[N]` in prose match entries in footnotes array |
| New discovery | `is_new: true` footnotes create KnownFact entries in game state |
| Callback reference | `is_new: false` footnotes include valid `fact_id` linking to existing KnownFact |
| Category tagging | Each footnote has a `FactCategory` (Lore, Place, Person, Quest, Ability) |
| Empty suppression | No footnotes section emitted when narrator reveals nothing new and references nothing |
| Graceful fallback | If narrator omits footnotes or markers don't match, narration still displays (degraded, no footnotes) |
