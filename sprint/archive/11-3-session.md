---
story_id: "11-3"
jira_key: "none"
epic: "11"
workflow: "tdd"
---
# Story 11-3: Lore seed — bootstrap store from genre pack lore entries and character creation anchors

## Story Details
- **ID:** 11-3
- **Title:** Lore seed — bootstrap store from genre pack lore entries and character creation anchors
- **Points:** 3
- **Priority:** P1
- **Workflow:** TDD
- **Stack Parent:** 11-2 (LoreStore) — merged
- **Repository:** sidequest-api (Rust)
- **Branch:** feat/11-3-lore-seed

## Context & Dependencies

### Story 11-1: LoreFragment Model (DONE)
- Defines the `LoreFragment` type with:
  - `id`: unique identifier
  - `category`: LoreCategory enum (History, Geography, Faction, Character, Item, Event, Language, Custom)
  - `content`: narrative text
  - `token_estimate`: auto-computed from content (~4 chars per token)
  - `source`: LoreSource enum (GenrePack, CharacterCreation, GameEvent)
  - `turn_created`: optional turn number
  - `metadata`: arbitrary key-value pairs

### Story 11-2: LoreStore (DONE)
- In-memory indexed collection of LoreFragments with:
  - `add()`: insert fragments, reject duplicates
  - `query_by_category()`: filter by LoreCategory
  - `query_by_keyword()`: case-insensitive content search
  - `total_tokens()`: sum of all fragments
  - `len()`, `is_empty()`: collection size

## What This Story Delivers

The lore seed system bootstraps a `LoreStore` with initial fragments from two sources:

### 1. Genre Pack Lore
Read lore entries from genre pack YAML files and create LoreFragments:
- **Genre-level lore** (`genre_pack.lore`):
  - `world_name`, `history`, `geography`, `cosmology` → LoreCategory::History/Geography
  - `factions[].name` + `factions[].description` → LoreCategory::Faction
  - All fragments: `source: LoreSource::GenrePack`, `turn_created: None`

- **World-level lore** (if loading a world):
  - Same structure as genre-level, plus legends and additional fields
  - `source: LoreSource::GenrePack`

### 2. Character Creation Anchors
Create LoreFragments from character creation choices to provide narrative anchors:
- Each `CharCreationScene` choice becomes a lore fragment:
  - `label` + `description` → concatenated as `content`
  - `category`: LoreCategory::Character (these anchor character identity)
  - `source: LoreSource::CharacterCreation`
  - `id`: formatted as `char_creation_{scene_id}_{choice_index}`
  - `metadata`: include `scene_id`, `choice_index`, plus any relevant mechanical effects

### 3. Integration Point
The function signature should be something like:
```rust
pub fn seed_lore_store(
    store: &mut LoreStore,
    genre_pack: &GenrePack,
    character_creation_scenes: &[CharCreationScene],
) -> Result<(), String>
```

Or if loading a specific world:
```rust
pub fn seed_lore_store_with_world(
    store: &mut LoreStore,
    genre_pack: &GenrePack,
    world: &World,
    character_creation_scenes: &[CharCreationScene],
) -> Result<(), String>
```

## Implementation Requirements

### Location
- Extend `/Users/keithavery/Projects/oq-2/sidequest-api/crates/sidequest-game/src/lore.rs`
- Add public functions for seeding the store
- Keep the seeding logic close to the LoreStore implementation

### Key Tasks
1. **Genre Pack Lore Loading:**
   - Iterate `genre_pack.lore.history` → create History fragment (id: `lore_genre_history`)
   - Iterate `genre_pack.lore.geography` → create Geography fragment (id: `lore_genre_geography`)
   - Iterate `genre_pack.lore.cosmology` → create History fragment (id: `lore_genre_cosmology`)
   - For each faction in `genre_pack.lore.factions`:
     - Create Faction fragment from `name` + `description`
     - ID: `lore_genre_faction_{faction_name_slugified}`
     - Metadata: include `faction_name`

2. **World Lore Loading (Optional):**
   - If a `World` is provided, also load world-level lore with same structure
   - World fragments take precedence (higher in narrative hierarchy)
   - ID prefix: `lore_world_{world_slug}_*`

3. **Character Creation Anchors:**
   - Iterate through `character_creation_scenes`
   - For each scene, iterate choices
   - Create one fragment per choice:
     - `label` + `description` → `content`
     - Category: LoreCategory::Character
     - ID: `lore_char_creation_{scene_id}_{choice_index}`
     - Metadata keys: `scene_id`, `choice_index`, `choice_label`
     - If mechanical effects have relevant fields (background, class_hint, race_hint, etc.), add to metadata

4. **Error Handling:**
   - Gracefully handle duplicate IDs (shouldn't happen with the naming scheme, but be safe)
   - Return `Result<(), String>` with descriptive errors if fragments can't be added
   - Consider whether empty lore sections should produce empty fragments or be skipped

5. **Tests (TDD):**
   - Test seeding from genre pack lore fields
   - Test seeding from character creation scenes
   - Test that all fragments have correct sources and categories
   - Test that token estimates are computed correctly
   - Test that metadata is preserved
   - Test combining both genre pack and character creation anchors
   - Test duplicate fragment handling
   - Test with empty/optional lore sections

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-27T00:00:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27T00:00:00Z | - | - |

## Delivery Findings

No upstream findings yet. Discoveries logged as work progresses.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

No deviations from spec yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Code Architecture Notes

### GenrePack Structure (from sidequest-genre)
```rust
pub struct GenrePack {
    pub lore: Lore,  // Contains history, geography, cosmology, factions
    pub char_creation: Vec<CharCreationScene>,
    pub worlds: HashMap<String, World>,
    // ... other fields
}

pub struct Lore {
    pub world_name: String,
    pub history: String,
    pub geography: String,
    pub cosmology: String,
    pub factions: Vec<Faction>,
    pub extras: HashMap<String, serde_json::Value>,
}

pub struct Faction {
    pub name: String,
    pub description: String,
    pub disposition: String,
    pub extras: HashMap<String, serde_json::Value>,
}

pub struct CharCreationScene {
    pub id: String,
    pub title: String,
    pub narration: String,
    pub choices: Vec<CharCreationChoice>,
}

pub struct CharCreationChoice {
    pub label: String,
    pub description: String,
    pub mechanical_effects: MechanicalEffects,
}
```

### LoreStore API (from story 11-2)
```rust
impl LoreStore {
    pub fn new() -> Self { ... }
    pub fn add(&mut self, fragment: LoreFragment) -> Result<(), String> { ... }
    pub fn query_by_category(&self, category: &LoreCategory) -> Vec<&LoreFragment> { ... }
    pub fn query_by_keyword(&self, keyword: &str) -> Vec<&LoreFragment> { ... }
    pub fn total_tokens(&self) -> usize { ... }
    pub fn len(&self) -> usize { ... }
    pub fn is_empty(&self) -> bool { ... }
}
```

### LoreFragment Constructor (from story 11-1)
```rust
impl LoreFragment {
    pub fn new(
        id: String,
        category: LoreCategory,
        content: String,
        source: LoreSource,
        turn_created: Option<u64>,
        metadata: HashMap<String, String>,
    ) -> Self { ... }
}
```

## Example: Low Fantasy Genre Pack
```yaml
# Genre level lore
lore:
  world_name: The Shattered Reach
  history: "Three generations ago, the Reach was one kingdom..."
  geography: "The Shattered Reach spans a broad river valley..."
  cosmology: "The people of the Reach hold no unified theology..."
  factions:
    - name: "The Merchant Consortium"
      description: "A coalition of wealthy trading families..."
    - name: "The Order of the Ashen Veil"
      description: "A religious order devoted to the cult..."
```

Would produce:
- `lore_genre_history` → History category, content from `world_name` + `history`
- `lore_genre_geography` → Geography category
- `lore_genre_cosmology` → History category
- `lore_genre_faction_merchant_consortium` → Faction category
- `lore_genre_faction_order_of_the_ashen_veil` → Faction category

Character creation would add:
- `lore_char_creation_origins_0` → Character, "The Hearthlands: You grew up..."
- `lore_char_creation_origins_1` → Character, "The Stone Halls: You were raised..."
- ... (one per choice, across all scenes)
