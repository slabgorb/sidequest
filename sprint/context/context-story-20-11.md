---
parent: context-epic-20.md
workflow: tdd
---

# Story 20-11: item_acquire sidecar tool — narrator calls tool to grant items, sidecar parser validates and feeds assemble_turn

## Business Context

**ADR-057** — Narrator Crunch Separation. Stories 20-1 through 20-10 built the infrastructure for tool-based mechanical extraction. But most tools are still **not wired into the production pipeline**.

This story fixes the first broken tool: **item_acquire**. After story 20-8 deleted `extractor.rs`, item acquisition is completely broken:
- Narrator narrates "You find a rusty sword"
- Inventory never updates (items_gained always empty)
- Player sees narration with zero mechanical backing
- **OTEL silent** — no way to tell if narrator intended the item grant

The fix: **Wire item_acquire as a sidecar tool** following the pattern established in story 20-10 (tool call parsing). Narrator calls the tool *before* narrating the acquisition, tool returns validated item data, `assemble_turn` feeds it into `items_gained`, state patch applies inventory changes.

**Depends on:** Stories 20-1 through 20-10 (all landed). Story 20-12 (merchant_transact) depends on this pattern.

## Technical Design

### Current State

**What exists (from story 20-3, never completed wiring):**
- Tool definition: `sidequest-agents/src/tools/item_acquire.rs` exists (or should)
- Struct: `ItemAcquireCall { item_ref: String, source: String }` (or similar)
- Parser stub: Tool parser probably exists but doesn't handle item_acquire

**What's broken:**
- Tool is NOT in the `--allowedTools` list in `client.rs`
- Tool call results are NOT parsed in `tool_call_parser.rs`
- `ToolCallResults` struct (story 20-1) has NO `items_acquired` field — needs to be added
- `assemble_turn` (story 20-1) does NOT populate `items_gained` from tool results
- OTEL spans for item acquisition are NOT emitted

**Where the gap shows:**
```rust
// orchestrator.rs line ~701
let mut base = assemble_turn(extraction, rewrite, flags, ToolCallResults::default());
// ToolCallResults::default() = { scene_mood: None, scene_intent: None, ... items_acquired: None, ... }
// items_gained never populated
```

**NarratorExtraction (story 20-9, now post-tool-call):**
```rust
pub struct NarratorExtraction {
    pub items_gained: Vec<InventoryDelta>,  // Always empty—no parser fed it
    // ... other fields
}
```

### What Must Change

**1. Extend ToolCallResults struct**
File: `crates/sidequest-agents/src/tools/assemble_turn.rs`
```rust
pub struct ToolCallResults {
    pub scene_mood: Option<String>,
    pub scene_intent: Option<String>,
    pub items_acquired: Option<Vec<ItemAcquireResult>>,  // NEW
    // ... other fields (scene_render, quest_update, lore_mark, etc.)
}
```

New struct:
```rust
pub struct ItemAcquireResult {
    pub item_id: ItemId,
    pub name: String,
    pub source: String,  // "narrator-described", "catalog-lookup", or source name
}
```

**2. Add item_acquire to allowed tools**
File: `crates/sidequest-agents/src/client.rs` (~line 150)
Currently: `--allowedTools 'Bash(set_mood)', 'Bash(set_intent)', ...`
Add: `'Bash(item_acquire)'`

**3. Implement item_acquire tool script**
Location: `.sidequest_scripts/item_acquire.sh` or similar (check how other scripts are stored)
Signature: `item_acquire --item-ref "sword" --source "merchant"`
Output: JSON `{ "tool": "item_acquire", "result": { "item_id": "iron_sword", "name": "Iron Sword", "source": "merchant" } }`
Writes to sidecar JSONL (story 20-10 pattern)

**4. Parse item_acquire tool calls**
File: `crates/sidequest-agents/src/tools/tool_call_parser.rs` (~story 20-10)
Add handler for `{ "tool": "item_acquire", ... }` records
Validate against genre pack item_catalog
Return `ToolCallResults { items_acquired: Some([...]), ... }`

**5. Wire into assemble_turn**
File: `crates/sidequest-agents/src/tools/assemble_turn.rs`
```rust
pub fn assemble_turn(
    extraction: NarratorExtraction,
    rewrite: ActionRewrite,
    flags: ActionFlags,
    tools: ToolCallResults,  // Include tool results
) -> ActionResult {
    let mut result = /* base construction */;
    
    // Handle tool-provided items
    if let Some(items) = tools.items_acquired {
        result.items_gained.extend(
            items.into_iter().map(|item| InventoryDelta { ... })
        );
    }
    
    result
}
```

**6. OTEL instrumentation**
Emit spans for:
- Tool call invoked: `item_acquire called with item_ref={ref} source={source}`
- Validation result: `item_acquire resolved to item_id={id} name={name}`
- State patch applied: `inventory_delta applied: {item_id} quantity=+1`

### Item Resolution Pattern

Handle both catalog lookups and narrator-described items:

**Case 1: Catalog Lookup**
- Input: `item_ref = "basic_sword"` (exact catalog key)
- Parser finds in genre pack's `item_catalog`
- Output: `ItemAcquireResult { item_id: "basic_sword", name: "Basic Sword", source: "catalog" }`

**Case 2: Narrator-Described Item**
- Input: `item_ref = "a rusty sword with strange runes"` (not in catalog)
- Parser cannot find exact match
- **Don't fail silently.** Instead:
  - Synthesize ItemId from narrator description (hash or slug generator)
  - Log to OTEL: `item_acquire improvised item_id={synth_id} from description="{ref}"`
  - Return `ItemAcquireResult { item_id: synth_id, name: item_ref, source: "narrator-described" }`

**Case 3: Invalid Reference**
- Input: `item_ref = "does_not_exist"` AND not a plausible description
- **FAIL LOUDLY.** Don't add item.
- Log to OTEL: `item_acquire FAILED: item_ref="{ref}" not found in catalog, rejected as invalid`
- Increment tracing counter: `action_tool_failures{tool="item_acquire"}`

### Testing Strategy

**Unit Tests (RED phase):**
1. Parser validates catalog lookups ✓
2. Parser synthesizes items for descriptions ✓
3. Parser rejects invalid references ✓
4. assemble_turn populates items_gained from tool results ✓

**Integration Tests:**
1. Narrator calls item_acquire → tool writes to sidecar → parser reads → items_gained populated ✓
2. Full wiring: orchestrator invokes narrator → tool call → assemble_turn → state patch → inventory updated ✓

**Wiring Test (critical — AC5):**
- Production code path exercises item_acquire (not mocked, not test-only)
- Verify via OTEL spans or inventory inspection in playtest

## Dependencies & Blockers

- **Depends on:** Stories 20-1 (assemble_turn), 20-10 (tool call parser), genre pack loading (story 15-7)
- **No blockers** (item_acquire tool definition should exist from 20-3)
- **Sibling story:** 20-12 (merchant_transact) depends on this for the item resolution pattern

## Acceptance Criteria Breakdown

| AC | Status | Notes |
|----|--------|-------|
| AC1 — Tool wired into sidecar pipeline | RED | Add to `--allowedTools`, parse in tool_call_parser |
| AC2 — Parser validates catalog + improves | RED | Catalog lookup, synthesize for descriptions, reject invalid |
| AC3 — assemble_turn feeds into items_gained | GREEN | Extend ToolCallResults, populate items_gained, apply patches |
| AC4 — Tests verify full pipeline | RED/GREEN | Unit: parser, Integration: narrator → items_gained, Wiring: production path |
| AC5 — No regressions | VERIFY | All other tools (scene_mood, lore_mark, quest_update) remain green |

## Key Files to Touch

| File | Changes |
|------|---------|
| `crates/sidequest-agents/src/tools/assemble_turn.rs` | Add `items_acquired` to ToolCallResults, populate items_gained |
| `crates/sidequest-agents/src/tools/tool_call_parser.rs` | Add item_acquire parser handler, validate against catalog |
| `crates/sidequest-agents/src/client.rs` | Add `Bash(item_acquire)` to allowedTools |
| `crates/sidequest-game/src/item.rs` or similar | May need ItemId synthesis logic for narrator-described items |
| Tests: `tests/item_acquire_story_20_11_tests.rs` | NEW — full suite |

## References

- **ADR-057:** `docs/adr/057-narrator-crunch-separation.md`
- **Story 20-1:** `sprint/context/context-story-20-1.md` — assemble_turn infrastructure
- **Story 20-10:** `sprint/context/context-story-20-10.md` — tool call parser pattern
- **Story 20-3:** Tool definition (should have ItemAcquireCall or similar)
