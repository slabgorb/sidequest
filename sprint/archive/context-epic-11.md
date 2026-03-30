# Epic 11: Lore & Language — RAG Retrieval, Conlang Name Banks

## Overview

Build two interrelated subsystems: a **lore store** that collects and retrieves narrative
facts for agent prompt context, and a **conlang name bank** that provides linguistically
consistent names from genre pack language rules.

The lore system solves the "context amnesia" problem — without it, the narrator only sees
the current game snapshot plus genre pack flavor text. With it, agents can retrieve relevant
history ("the party once betrayed the merchant guild"), world facts ("the northern bridge
was destroyed in the siege"), and character backstory. Lore accumulates as the game
progresses: things that happen become indexed facts.

The name bank system solves the "linguistic chaos" problem — without it, the narrator
freehands names and produces inconsistent results (one Elvish name uses Germanic roots,
another uses Japanese). Name banks pre-generate names from morpheme glossaries so every
name in a language follows the same phonotactic and semantic rules.

## Background

### Python Reference: sq-2/sidequest/lore/

The Python lore system has 8 files:

| File | Purpose |
|------|---------|
| `models.py` | LoreFragment, LoreCategory, LoreSource |
| `store.py` | In-memory indexed collection |
| `seed.py` | Bootstrap from genre pack + character creation |
| `retriever.py` | Query interface (dispatches to static or semantic) |
| `static_retriever.py` | Category + keyword filtering |
| `chunker.py` | Splits large text into token-bounded fragments |
| `worker.py` | Background lore accumulation from game events |
| `embedding_retriever.py` | Embedding-based semantic similarity search |

Key design decisions carried forward:
- Fragments carry token estimates so agents can budget context window
- Categories are enumerated (History, Geography, Faction, etc.) plus Custom(String)
- Source tracking distinguishes genre_pack lore from game-generated lore
- Static retrieval (category + keyword) is the primary path; semantic retrieval is optional

### Python Reference: sq-2 Epic 63 (Conlang Name Banks)

The conlang system ships morpheme glossaries with genre packs. Each language defines
morphemes (form + meaning + position), and the name generator composes them into glossed
names. Example:

```
"Thal'verath" = thal(shadow) + vera(keeper) + th(honorific)
```

This ensures all names in a language share phonetic patterns and meaningful structure.
The narrator draws from the bank instead of inventing names on the fly.

### Connection to Other Systems

The lore system is a **foundation epic** — other epics depend on it:
- Epic 10 (OCEAN): personality shifts become lore fragments
- Epic 9 (KnownFact): language comprehension grows through lore-indexed exposure
- Future scenario/mystery epics: clues are lore-indexed facts with restricted visibility

## Technical Architecture

### Lore System Data Model

```rust
pub struct LoreFragment {
    pub id: String,
    pub category: LoreCategory,
    pub content: String,
    pub token_estimate: usize,
    pub source: LoreSource,
    pub turn_created: Option<u64>,  // None for genre_pack / char creation
    pub metadata: HashMap<String, String>,
}

pub enum LoreCategory {
    History,
    Geography,
    Faction,
    Character,
    Item,
    Event,
    Language,
    Custom(String),
}

pub enum LoreSource {
    GenrePack,
    CharacterCreation,
    GameEvent,
}
```

### Lore Data Flow

```
Bootstrap (session start)               Accumulation (during play)
─────────────────────────               ──────────────────────────
genre_pack.lore_entries ──► seed()      world_state_agent
character_creation      ──► seed()          │
                              │             ├─ "The merchant guild
                              ▼             │   declared war on the
                         ┌──────────┐       │   thieves' quarter"
                         │LoreStore │◄──────┘
                         │          │       lore_store.add(fragment)
                         │ indexed  │
                         │ by cat,  │
                         │ keyword, │
                         │ (embed)  │
                         └────┬─────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         static_query    semantic_query   token_budget
         (category +     (embedding        (agents request
          keyword)        similarity)       up to N tokens
                                            of relevant lore)
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                     Agent Prompt Context
                     "Relevant lore:
                      - The merchant guild..."
```

### Name Bank Data Model

```rust
pub struct MorphemeGlossary {
    pub language_name: String,   // "High Elvish"
    pub phonotactics: String,    // optional pronunciation rules
    pub morphemes: Vec<Morpheme>,
}

pub struct Morpheme {
    pub form: String,            // "thal"
    pub meaning: String,         // "shadow"
    pub position: MorphemePosition,
}

pub enum MorphemePosition {
    Prefix,
    Root,
    Suffix,
}

pub struct GlossedName {
    pub display: String,         // "Thal'verath"
    pub gloss: Vec<(String, String)>, // [("thal","shadow"), ("vera","keeper"), ...]
    pub language: String,        // "High Elvish"
}
```

### Name Bank Data Flow

```
Genre Pack YAML                     Name Generation
───────────────                     ───────────────
languages:                          generate_name_bank()
  high_elvish:                          │
    morphemes:                          ├─ load glossary
      - form: thal                      ├─ compose names from morphemes
        meaning: shadow                 │   respecting position rules
        position: root                  ├─ produce GlossedName list
      - form: vera                      └─ cache in NameBank
        meaning: keeper
        position: root              Narrator Prompt
      - form: th                    ──────────────
        meaning: honorific          compose_prompt()
        position: suffix                │
                                        ├─ "Available High Elvish names:
                                        │    Thal'verath (shadow-keeper)
                                        │    Miravel (star-singer)
                                        │    ..."
                                        └─ narrator picks from bank
                                           instead of inventing
```

### Language Knowledge Integration (11-10)

```
KnownFact system (Epic 9)
    │
    ├─ early game: foreign text is opaque
    │    "The sign reads: 'ᚦᚨᛚ ᚹᛖᚱᚨᚦ'"
    │
    ├─ after exposure: partial comprehension
    │    "The sign reads something about shadows"
    │
    └─ after study: full transliteration
         "The sign reads: 'Thal'verath — shadow keeper'"

Language comprehension tracked as KnownFact entries.
Morpheme meanings unlock progressively through play.
```

## Story Dependency Graph

```
2-5 (orchestrator turn loop)
 │
 ├──► 11-1 (LoreFragment model)
 │     │
 │     ├──► 11-2 (LoreStore — add, query by category/keyword)
 │     │     │
 │     │     ├──► 11-3 (lore seed from genre pack + char creation)
 │     │     │
 │     │     ├──► 11-4 (lore injection into agent prompts)
 │     │     │
 │     │     ├──► 11-5 (lore accumulation from game events)
 │     │     │
 │     │     └──► 11-6 (semantic retrieval — optional embedding RAG)
 │     │
 │     └──► 11-7 (morpheme glossary schema)
 │           │
 │           └──► 11-8 (name bank generation)
 │                 │
 │                 └──► 11-9 (narrator name injection)
 │                       │
 │                       └──► 11-10 (language knowledge as KnownFact)
 │                                    ↑ also depends on Epic 9
```

## Deferred (Not in This Epic)

- **Persistent lore storage** — LoreStore is in-memory for now. Persisting to SQLite
  or file for cross-session continuity is a save/load concern (Epic 2 story 2-4
  or a dedicated persistence epic).
- **Lore editing UI** — No UI for viewing or editing lore fragments. This is
  narrator-facing context, not player-facing content.
- **Embedding model selection** — Story 11-6 (semantic retrieval) defines the
  interface but does not prescribe a specific embedding model. Model choice is
  deferred to implementation time.
- **Lore conflict resolution** — When two fragments contradict each other (e.g.,
  "the bridge was destroyed" vs. "the party crossed the bridge"), no automated
  resolution. The narrator sees both and decides.
- **Procedural language generation** — Morpheme glossaries are hand-authored in
  genre packs. Generating entire conlangs procedurally is out of scope.
- **Voice synthesis integration** — Pronunciation rules in glossaries could feed
  TTS phoneme hints. This is a daemon concern, not an API concern.

## Dependencies

### From Epic 2 (must complete first)
- Story 2-5: Orchestrator turn loop (11-1 depends on game state existing)
- Genre pack loader: lore seed (11-3) reads from genre pack YAML
- Agent prompt composition: lore injection (11-4) hooks into existing prompt builder

### From Epic 9 (soft dependency)
- KnownFact system: story 11-10 (language knowledge) depends on the KnownFact
  model from Epic 9. This is the last story in the epic and can wait.

### No Dependency On
- Epic 10 (OCEAN): OCEAN shifts can become lore fragments, but that's Epic 10's
  responsibility to emit them. The lore store just accepts whatever is added.
- Epic 3 (Game Watcher): Lore operations are observable but don't require the watcher.

## Success Criteria

During a playtest session:
1. The lore store is seeded at session start with genre pack entries and character
   creation anchors
2. Agents can query the store by category and keyword, receiving relevant fragments
   within a token budget
3. As the game progresses, new lore fragments are created from significant game events
4. Narrator prompts include relevant lore context — the narrator references past events
   accurately instead of contradicting or forgetting them
5. NPC and location names are drawn from name banks, not invented ad hoc
6. All names in a given language share consistent phonetic patterns
7. Name glosses are available (the system knows "Thal'verath" means "shadow-keeper")
8. (If Epic 9 is complete) Foreign text comprehension grows through play — early
   encounters show opaque text, later encounters show partial or full translations
