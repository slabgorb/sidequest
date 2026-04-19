---
story_id: "11-10"
epic: "11"
epic_title: "Lore & Language — RAG Retrieval, Conlang Name Banks"
workflow: "tdd"
---
# Story 11-10: Language knowledge as KnownFact — track which conlang words/phrases a character has learned during play

## Story Details
- **ID:** 11-10
- **Title:** Language knowledge as KnownFact — track which conlang words/phrases a character has learned during play
- **Points:** 2
- **Priority:** p2
- **Epic:** 11 — Lore & Language
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Stack Parent:** 11-1 (LoreFragment model — merged) and 11-7 (Morpheme glossary — merged)

## Story Description

When a character encounters and learns a conlang word or phrase during play, that knowledge should be recorded as a `LoreFragment` with category `Language` so the narrator can track what the character understands about the game's constructed language.

This story bridges the lore system (11-1, 11-2, 11-4) and the conlang system (11-7, 11-8) by providing a way to record language knowledge as learnable facts.

### System Responsibilities

**Recording Language Knowledge:**
- Define a function to create a `LoreFragment` from a morpheme or name that a character learns
- Store language knowledge with category `Language` and metadata about:
  - Which language (e.g., "elvish", "draconic")
  - What was learned (morpheme string, meaning, pronunciation)
  - When it was learned (turn number)
  - Which character learned it (metadata)

**Querying Language Knowledge:**
- Provide a method to query what a character knows about a specific language
- Retrieve all language knowledge fragments for a character
- Filter by language ID to get language-specific knowledge

### Implementation Notes

**Core Structures:**
- Use `LoreCategory::Language` (already exists in lore.rs)
- Store morpheme data in `LoreFragment.metadata` as key-value pairs:
  - `morpheme` — the word/phrase string
  - `meaning` — semantic gloss
  - `pronunciation` — pronunciation hint
  - `language_id` — which conlang (e.g., "elvish")
  - `learned_by_character` — character ID or name

**Fragment ID Naming:**
- Use pattern: `lang_known_<language_id>_<morpheme>_<character_id>_<turn>`
- Example: `lang_known_elvish_zar_hero_42` (fire morpheme learned at turn 42)

**Key Function:**
- `fn language_knowledge_fragment(morpheme: &Morpheme, character_id: &str, turn_number: u64) -> LoreFragment`
  - Creates a language fragment with all necessary metadata
  - Auto-estimates tokens from content

**Query Function:**
- `fn query_language_knowledge(store: &LoreStore, language_id: &str, character_id: Option<&str>) -> Vec<&LoreFragment>`
  - Returns all language fragments, optionally filtered by character
  - Allows narrator to see what a character knows or what's known about a language

### Target Modules

The implementation will likely touch:
- `crates/sidequest-game/src/lore.rs` — Add language knowledge helper functions
- `crates/sidequest-game/src/conlang.rs` — Export Morpheme metadata for fragment creation
- `crates/sidequest-game/src/lib.rs` — Expose new functions

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Language fragment creation | `language_knowledge_fragment()` creates LoreFragment with Language category |
| Metadata storage | morpheme, meaning, pronunciation, language_id, character_id stored in metadata |
| ID formatting | Fragment IDs follow pattern `lang_known_<language_id>_<morpheme>_<character_id>_<turn>` |
| Turn tracking | `turn_created` field populated with turn number |
| Query by language | `query_language_knowledge()` returns all Language fragments for a given language |
| Query by character | Query function supports optional character filter |
| Token estimation | Fragments include reasonable token estimates |
| Integration with Morpheme | Functions accept &Morpheme from conlang module |
| Module exposure | New functions exported from lib.rs for use in game state |
| Tests | Unit tests verify fragment creation and querying |

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-28T02:13:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-28T02:13:32Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
