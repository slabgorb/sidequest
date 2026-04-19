---
story_id: "20-11"
jira_key: ""
epic: "20"
workflow: "tdd"
---

# Story 20-11: item_acquire sidecar tool — narrator calls tool to grant items, sidecar parser validates and feeds assemble_turn

## Story Details
- **ID:** 20-11
- **Title:** item_acquire sidecar tool — narrator calls tool to grant items, sidecar parser validates and feeds assemble_turn
- **Jira Key:** (Personal project — no Jira)
- **Epic:** 20 — Narrator Crunch Separation — Tool-Based Mechanical Extraction (ADR-057)
- **Workflow:** tdd
- **Points:** 5
- **Priority:** p0
- **Repos:** sidequest-api
- **Stack Parent:** none

## Context & Problem

After story 20-8 (delete extractor.rs), the item_acquire mechanical extraction is completely broken. The narrator narrates item grants but no inventory update happens because:

1. **extractor.rs is gone** — the 3-tier JSON recovery pipeline was deleted
2. **items_gained always empty** — NarratorExtraction returns empty vector, no items flow through
3. **Tool definition exists** (20-3) but never wired into the sidecar call pipeline
4. **Narrator narrates without effect** — lore consistency failure; player sees "you got a sword" but inventory stays unchanged

Generation pattern: **Call tool FIRST, narrate around result** (not narrate then extract).

## Acceptance Criteria

- [x] **AC1:** item_acquire tool call is fully wired in the sidecar tool call pipeline
  - Tool definition is recognized by narrator prompt
  - Tool output is captured in ToolCallResults
  - Parser validates tool calls and extracts ItemAcquireCall structs

- [x] **AC2:** Parser validates item references against genre pack item_catalog
  - Existing items (catalog lookups) resolve to ItemId
  - Narrator-described items (improvised) create synthesized ItemId
  - Invalid item references fail gracefully (error logged, no silent fallbacks)

- [x] **AC3:** assemble_turn feeds item_acquire results into items_gained
  - items_gained vector populates from tool calls
  - State patching applies inventory changes correctly
  - OTEL spans log item acquisitions (source, item_id, narrator/origin)

- [x] **AC4:** Tests verify full pipeline
  - Unit: parser validates catalog lookups and improvised items
  - Integration: tool call → parser → assemble_turn → ActionResult with items_gained
  - Wiring test: production code path exercises item_acquire (not test-only)

- [x] **AC5:** No regressions in other tool pipelines (scene_mood, lore_mark, quest_update, etc.)

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-02T22:19Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T22:19Z | - | - |

## Delivery Findings

No upstream findings.

## Design Deviations

None yet.
