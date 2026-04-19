---
story_id: "15-16"
jira_key: "none"
epic: "none"
workflow: "tdd"
---

# Story 15-16: Wire merchant system — execute_buy/sell/calculate_price/format_merchant_context all unwired

## Story Details
- **ID:** 15-16
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** tdd
**Phase:** green
**Phase Started:** 2026-04-02T00:00:30Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-01T00:00:00Z | 2026-04-01T23:49:29Z | 23h 49m |
| red | 2026-04-01T23:49:29Z | 2026-04-02T00:00:30Z | 11m 1s |
| green | 2026-04-02T00:00:30Z | - | - |

## Story Context

The merchant subsystem in `sidequest-game/src/merchant.rs` is **complete and fully tested**:
- `calculate_price()` — applies disposition-based markup/discount per ADR-020
- `execute_buy()` — atomic transaction with inventory mutation and gold transfer
- `execute_sell()` — seller submits item, buyer receives gold (no gold limit on merchants)
- `format_merchant_context()` — formats merchant inventory for narrator prompt injection

**Zero callers** exist in the server, agents, or game state code. The system is wired nowhere.

### Wiring Requirements

**Two integration points:**

1. **Merchant Context Injection (Narrator Prompt)**
   - When intent is `Exploration` or `Dialogue` AND the current location has an NPC with role containing "merchant"
   - Extract the merchant's inventory and disposition from the NPC registry/game state
   - Call `format_merchant_context(merchant_name, inventory, disposition)` 
   - Inject the result into the narrator's prompt (Situational zone, before state summary)
   - OTEL event: `merchant.context_injected` with tags: merchant_name, item_count

2. **Merchant Transaction Execution (Narrator → State)**
   - When the narrator's `WorldStatePatch` contains a `MerchantTransaction`
   - Call `execute_buy()` or `execute_sell()` to mechanically resolve it
   - Apply inventory/gold mutations to the player character and merchant NPC
   - Return OTEL event: `merchant.transaction` with tags: transaction_type, item_name, price, gold_before, gold_after

### Architecture Notes

- **NPC Registry:** GameSnapshot.npc_registry contains Vec<NpcRegistryEntry> with name, role, location
- **Merchant Detection:** Check `role` field for substring match "merchant"
- **Disposition Source:** Game state has the actual Npc with disposition; registry is summary-only
- **Intent Routing:** IntentRouter classifies to `Intent::Exploration` or `Intent::Dialogue`
- **Agent Dispatch:** Narrator agent (for Exploration), Ensemble agent (for Dialogue)
- **Context Builder:** Orchestrator uses ContextBuilder to assemble prompt zones
- **State Patches:** Narrator extracts items_gained, npcs_present, quest_updates as JSON; merchant transaction is a WorldStatePatch mutation

## Sm Assessment

**Story:** 15-16 — Wire merchant system
**Points:** 5 | **Workflow:** TDD (phased) | **Repos:** api

**Assessment:** Clean wiring story. The merchant subsystem (`merchant.rs`) is fully implemented and tested — `calculate_price`, `execute_buy`, `execute_sell`, `format_merchant_context` all exist with zero callers. Two integration points needed: (1) inject merchant context into narrator prompts when intent is Exploration/Dialogue and a merchant NPC is present, (2) execute merchant transactions mechanically from WorldStatePatch instead of letting the narrator hallucinate inventory changes. OTEL spans required for both paths.

**Risk:** Low. Code exists, tests exist, this is pure wiring.
**Recommendation:** Proceed to RED phase — Argus Panoptes writes failing integration tests for both wiring points.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Wiring story — two integration points with zero callers need compilation-verified test contracts.

**Test Files:**
- `crates/sidequest-agents/tests/merchant_wiring_story_15_16_tests.rs` — Context injection into narrator prompts (10 tests)
- `crates/sidequest-game/tests/merchant_wiring_story_15_16_tests.rs` — Mechanical transaction resolution + OTEL (12 tests)

**Tests Written:** 22 tests covering 2 ACs + OTEL requirements
**Status:** RED (compilation failures — ready for Dev)

**Three compilation gates Dev must resolve:**
1. `inject_merchant_context()` — public function on orchestrator module. Takes `&mut ContextBuilder`, NPC registry, NPCs, Intent, and current location. Injects `format_merchant_context()` output into Valley zone when intent is Exploration/Dialogue and a merchant NPC is at the player's location.
2. `MerchantTransactionRequest` — new type in `merchant.rs`. Lightweight struct with `transaction_type: TransactionType`, `item_id: String`, `merchant_name: String`. This is what the narrator outputs; the server resolves it mechanically.
3. `GameSnapshot::apply_merchant_transactions(&mut self, &[MerchantTransactionRequest])` — method that finds the named merchant NPC, calls `execute_buy()`/`execute_sell()` using the NPC's disposition, and returns `Vec<Result<MerchantTransaction, MerchantError>>`.

### Rule Coverage

| Rule | Applicability | Status |
|------|--------------|--------|
| #1 silent errors | N/A — no error swallowing in test code | — |
| #2 non_exhaustive | N/A — no new public enums in tests | — |
| #3 placeholders | N/A — test fixtures use realistic values | — |
| #4 tracing | Covered by 2 OTEL tests | failing |
| #5 constructors | N/A — tests consume existing validated types | — |
| #6 test quality | Self-checked: 22/22 tests have meaningful assertions | pass |
| #7 unsafe casts | N/A — no `as` casts in test code | — |
| #8 serde bypass | N/A — MerchantTransactionRequest will need serde; Dev must ensure validation | — |

**Rules checked:** 2 of 15 applicable (tracing, test quality). Others not applicable to test-only code.
**Self-check:** 0 vacuous tests found. All assertions are meaningful.

**Handoff:** To Hephaestus the Smith (Dev) for implementation.

## Delivery Findings

No upstream findings at setup.

### TEA (test design)
- No upstream findings during test design.

## Design Deviations

### TEA (test design)
- **inject_merchant_context as standalone function rather than inline in process_action**
  - Spec source: session context, AC-1
  - Spec text: "inject format_merchant_context() into the narrator prompt"
  - Implementation: Tests assume a public `inject_merchant_context()` function rather than testing via `process_action()` end-to-end
  - Rationale: `process_action()` requires a live Claude CLI subprocess — testing prompt assembly directly is more reliable and doesn't couple tests to LLM availability. Dev can call this function from within `process_action()`.
  - Severity: minor
  - Forward impact: none — Dev simply calls the tested function from the orchestrator
- **MerchantTransactionRequest as narrator-output type separate from MerchantTransaction**
  - Spec source: session context, AC-2
  - Spec text: "call execute_buy()/execute_sell() to mechanically resolve"
  - Implementation: Tests introduce `MerchantTransactionRequest` (item_id + merchant_name + type) distinct from `MerchantTransaction` (full resolution result with price, gold amounts)
  - Rationale: The narrator can't know the price (it depends on disposition-based calculation). The narrator outputs a request; the server resolves it mechanically. This separation enforces that prices are ALWAYS calculated server-side.
  - Severity: minor
  - Forward impact: none — clean separation of concerns