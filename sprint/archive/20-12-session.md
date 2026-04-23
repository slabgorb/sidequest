---
story_id: "20-12"
jira_key: ""
epic: "20"
workflow: "tdd"
---

# Story 20-12: merchant_transact sidecar tool — narrator calls tool to execute buy/sell, sidecar parser validates against merchant inventory

## Story Details
- **ID:** 20-12
- **Title:** merchant_transact sidecar tool — narrator calls tool to execute buy/sell, sidecar parser validates against merchant inventory
- **Jira Key:** (Personal project — no Jira)
- **Epic:** 20 — Narrator Crunch Separation — Tool-Based Mechanical Extraction (ADR-057)
- **Workflow:** tdd
- **Points:** 5
- **Priority:** p0
- **Repos:** sidequest-api
- **Stack Parent:** 20-11 (item_acquire sidecar tool)

## Context & Problem

After story 20-8 (delete extractor.rs), the merchant_transact mechanical extraction is completely broken:

1. **MerchantTransactionExtracted struct exists** (20-3) but always returns empty
2. **merchant_transactions always empty** — NarratorExtraction returns empty vector, no trades occur
3. **Tool definition exists** but never wired into the sidecar call pipeline
4. **Narrator narrates without effect** — lore consistency failure; player hears "you sold your sword" but gold/inventory unchanged

Generation pattern: **Call tool FIRST, execute transaction, narrate around result** (not narrate then extract).

This story depends on 20-11 (item_acquire) which established the sidecar tool pattern for mechanical inventory changes.

## Acceptance Criteria

- [ ] **AC1:** merchant_transact tool call is fully wired in the sidecar tool call pipeline
  - Tool definition is recognized by narrator prompt
  - Tool output is captured in ToolCallResults
  - Parser validates tool calls and extracts MerchantTransactCall structs

- [ ] **AC2:** Parser validates transaction details against merchant inventory
  - Merchant lookup by name (from genre pack merchant registry)
  - Item reference resolution (catalog or synthesized)
  - Gold validation (player has sufficient funds to buy, or valid items to sell)
  - Invalid transactions fail gracefully (error logged, no silent fallbacks)

- [ ] **AC3:** assemble_turn feeds merchant_transact results into merchant_transactions
  - merchant_transactions vector populates from tool calls
  - Inventory state patching applies buy/sell changes correctly
  - Gold state updates (deduct for buys, add for sells)
  - OTEL spans log transactions (merchant, item, type, gold_delta, origin)

- [ ] **AC4:** Tests verify full pipeline
  - Unit: parser validates merchant lookups, item resolution, and gold constraints
  - Integration: tool call → parser → assemble_turn → ActionResult with merchant_transactions
  - Wiring test: production code path exercises merchant_transact (not test-only)

- [ ] **AC5:** No regressions in other tool pipelines or item_acquire integration
  - item_acquire continues to work as baseline
  - merchant + player inventory state consistency

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-02T20:42Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-02T20:42Z | - | - |

## Delivery Findings

No upstream findings yet.

## Design Deviations

None yet.
