---
parent: context-epic-9.md
---

# Story 9-13: Journal Browse View

## Business Context

Players accumulate knowledge through play — lore, NPCs met, places discovered, quest
threads, ability revelations. The journal browse view gives them a dedicated screen to
review everything they've learned, organized by category and voiced in the genre style
of their world. Unlike a traditional quest log, this journal emerged entirely from play —
every entry was a narrator revelation, not a pre-authored objective.

This is the **browse layer** of the living journal system. It reads from the same
KnownFact store that the narrator injects into prompts (9-4) and that footnotes create
(9-11).

**Depends on:** Story 9-12 (footnote rendering — establishes the UI pattern)

## Technical Approach

### Data Source

The journal reads from the character's `known_facts: Vec<KnownFact>` in game state.
Each KnownFact has:
- `content` — the genre-voiced fact text
- `learned_turn` — when it was discovered
- `source` — Observation, Dialogue, Discovery
- `confidence` — Certain, Suspected, Rumored
- `category` — Lore, Place, Person, Quest, Ability (from 9-11's FactCategory)

### React UI

A new screen/panel in `sidequest-ui`:

1. **Category tabs:** Filter by Lore, Places, People, Quests, Abilities
2. **Entry list:** Each entry shows:
   - Fact content in genre voice
   - Source icon (eye for Observation, speech bubble for Dialogue, star for Discovery)
   - Confidence badge (Certain / Suspected / Rumored)
   - "Discovered Turn N" provenance
3. **Chronological or categorical sort** toggle
4. **Empty state:** "Your journal is empty. Explore the world to fill its pages."

### GameMessage

A new message type for requesting and receiving journal data:

```rust
// Client -> Server
GameMessage::JournalRequest

// Server -> Client
GameMessage::JournalResponse {
    entries: Vec<JournalEntry>,
}

struct JournalEntry {
    fact_id: String,
    content: String,
    category: String,
    source: String,
    confidence: String,
    learned_turn: u64,
}
```

### Access Pattern

The journal is requested on-demand (player opens journal view), not streamed.
This avoids unnecessary WebSocket traffic. The server reads from game state and
responds with the current fact set.

## Scope Boundaries

**In scope:**
- Journal browse screen in sidequest-ui
- Category filtering (Lore, Place, Person, Quest, Ability)
- Chronological and categorical sort
- Genre-voiced entry display with source and confidence
- `JournalRequest` / `JournalResponse` GameMessage types
- Server handler that reads KnownFacts from game state
- Empty state for new games

**Out of scope:**
- Player-authored journal entries (manual notes)
- Linking journal entries to specific narration history
- Search within journal
- Journal export or sharing
- Footnote cross-references from narration view to journal entries

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Browse screen | Dedicated journal view accessible from game UI |
| Category filter | Entries filterable by Lore, Place, Person, Quest, Ability |
| Genre voice | Entries display in genre-voiced content, not mechanical notation |
| Provenance | Each entry shows when it was discovered (turn number) |
| Confidence display | Entries show confidence level (Certain, Suspected, Rumored) |
| Source display | Entries show how the fact was learned (Observation, Dialogue, Discovery) |
| Sort options | Toggle between chronological and categorical ordering |
| Empty state | New games show appropriate empty journal message |
| On-demand loading | Journal data fetched when player opens view, not pre-streamed |
