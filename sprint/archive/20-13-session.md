---
story_id: "20-13"
jira_key: ""
epic: "20"
workflow: "tdd"
---

# Story 20-13: lore_mark sidecar tool — narrator calls tool to emit footnotes, sidecar parser collects into lore_established

## Story Details
- **ID:** 20-13
- **Title:** lore_mark sidecar tool — narrator calls tool to emit footnotes, sidecar parser collects into lore_established
- **Jira Key:** (Personal project — no Jira)
- **Epic:** 20 — Narrator Crunch Separation — Tool-Based Mechanical Extraction (ADR-057)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p1
- **Repos:** sidequest-api
- **Stack Parent:** 20-11 (item_acquire sidecar tool)

## Context & Problem

After story 20-8 (delete extractor.rs), the lore_mark mechanical extraction is completely broken:

1. **lore_established always None** — NarratorExtraction returns None, no lore facts flow through
2. **Footnote markers in prose ([1]) have no mechanical backing** — narrator uses footnote syntax but no extraction occurs
3. **Tool definition exists** (20-4) but never wired into the sidecar tool call pipeline
4. **Narrator narrates without effect** — lore facts mentioned in prose don't persist to player knowledge; repeated playthroughs contradict earlier facts

This story completes the Epic 20 migration — all mechanical extraction flows through sidecar tools, zero narrator JSON.

Generation pattern: **Call tool to establish fact, narrate around fact** (like item_acquire and merchant_transact).

This story depends on 20-11 (item_acquire) which established the sidecar tool pattern for mechanical changes during narration.

## Acceptance Criteria

- [ ] **AC1:** lore_mark tool call is fully wired in the sidecar tool call pipeline
  - Tool definition is recognized by narrator prompt
  - Tool output is captured in ToolCallResults
  - Parser validates tool calls and extracts LoreMarkCall structs

- [ ] **AC2:** Parser validates lore facts and confidence levels
  - Category field is recognized (world, npc, faction, location, quest, custom)
  - Confidence level is validated (high, medium, low)
  - Text field is non-empty and sanitized
  - Invalid lore marks fail gracefully (error logged, no silent fallbacks)

- [ ] **AC3:** assemble_turn feeds lore_mark results into lore_established
  - lore_established vector populates from tool calls
  - State patching applies lore changes correctly
  - Lore facts persist across turns and sessions
  - OTEL spans log lore establishments (category, confidence, text origin)

- [ ] **AC4:** Tests verify full pipeline
  - Unit: parser validates category, confidence, text fields
  - Integration: tool call → parser → assemble_turn → ActionResult with lore_established
  - Wiring test: production code path exercises lore_mark (not test-only)

- [ ] **AC5:** No regressions in other tool pipelines (item_acquire, merchant_transact, scene_mood, etc.)
  - Epic 20 migration is complete — all mechanical extraction flows through sidecar tools

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-03T01:40Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-03T01:40Z | - | - |

## Delivery Findings

No upstream findings yet.

## Design Deviations

None yet.
