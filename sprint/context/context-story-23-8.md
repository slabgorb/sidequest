---
parent: context-epic-23.md
workflow: tdd
---

# Story 23-8: Split state_summary blob into structured players and world-lore sections

## Business Context

The orchestrator currently injects a single `state_summary` string blob into the Valley/State zone.
This blob is assembled in `dispatch/prompt.rs` and contains everything: genre, world, location,
players (with inventory, abilities, quests), and NPCs. The prompt-reworked.md spec defines separate
`<players>` and `<world-lore>` sections with distinct structural contracts. Splitting enables:
- Independent token budgeting per section
- Different zone assignments if needed (players could move to Late for higher attention)
- Cleaner OTEL observability (per-section token counts)
- Foundation for lore filtering (23-4) which needs to operate on world-lore independently

## Technical Guardrails

- `dispatch/prompt.rs` (L10-L250+) builds `state_summary` as one `String` via `format!()` + `push_str()`
- The function signature returns `String` — TurnContext.state_summary is `Option<String>`
- **Interface change required:** Either split into two fields on TurnContext (`player_summary`, `world_lore_summary`) or return a struct with named fields
- The orchestrator (`orchestrator.rs` L396-L404) wraps state_summary in `<game_state>` tags
- `prompt-reworked.md` L95-L127 defines `<players>` with per-player character sheets
- `prompt-reworked.md` L130-L152 defines `<world-lore>` with locations, cultures, factions
- Inventory rules (L113-L117) are load-bearing — "items on list WORK, items not on list FAIL"
- Ability constraints (L119-L124) are load-bearing — "abilities not on list MUST fail"

## Scope Boundaries

**In scope:**
- Split `dispatch/prompt.rs` build function into `build_player_summary()` and `build_world_lore_summary()`
- Add both fields to TurnContext (or a PromptSummaries struct)
- Register as separate Valley sections in `build_narrator_prompt()`
- `<players>` section: per-player with name, HP, level, pronouns, inventory (canonical), abilities (hard constraint)
- `<world-lore>` section: world name, current location, cultures, locations, factions
- Preserve inventory and ability constraint language exactly from prompt-reworked.md
- Update `scripts/preview-prompt.py`

**Out of scope:**
- Moving players to a different zone (keep Valley for now)
- Lore filtering/RAG (23-4)
- Per-player perception rewriting (separate concern)

## AC Context

1. state_summary blob split into player_summary and world_lore_summary in dispatch/prompt.rs
2. TurnContext carries both fields (not one blob)
3. `<players>` section registered in Valley/State with per-player character sheets
4. `<world-lore>` section registered in Valley/Context with location, culture, faction data
5. Inventory constraint language preserved verbatim from prompt-reworked.md
6. Ability constraint language preserved verbatim from prompt-reworked.md
7. OTEL spans for each section with token counts
8. `scripts/preview-prompt.py` updated with both sections
