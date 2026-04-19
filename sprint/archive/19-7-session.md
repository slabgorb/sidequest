---
story_id: "19-7"
jira_key: "none"
epic: "19"
workflow: "tdd"
---

# Story 19-7: Weight-based encumbrance — total_weight, carry_mode, overencumbered state

## Story Details

- **ID:** 19-7
- **Jira Key:** none (personal project)
- **Epic:** 19 — Dungeon Crawl Engine
- **Workflow:** tdd (phased: setup → tea → dev → review → finish)
- **Points:** 3
- **Priority:** p1
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-06T23:01:22Z
**Round-Trip Count:** 1

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-06T14:40:00Z | 2026-04-06T18:36:05Z | 3h 56m |
| red | 2026-04-06T18:36:05Z | 2026-04-06T20:45:13Z | 2h 9m |
| green | 2026-04-06T20:45:13Z | 2026-04-06T20:58:53Z | 13m 40s |
| review | 2026-04-06T20:58:53Z | 2026-04-06T22:10:15Z | 1h 11m |
| green | 2026-04-06T22:10:15Z | 2026-04-06T22:30:31Z | 20m 16s |
| review | 2026-04-06T22:30:31Z | 2026-04-06T23:01:22Z | 30m 51s |
| finish | 2026-04-06T23:01:22Z | - | - |

## Story Summary

Add weight-based encumbrance to the inventory system. When enabled in genre rules (CarryMode::Weight), items have a total weight that cannot exceed weight_limit. Overencumbered state accelerates trope tick multiplier by 1.5x in room_graph mode.

**Key mechanics:**
- `Inventory.total_weight() -> f64` — sum of all items' weight × quantity
- `CarryMode` enum: `Count` (existing) or `Weight` (new)
- Weight validation on `Inventory.add()` — reject if would exceed limit
- `Inventory.is_overencumbered() -> bool` — true at or over weight_limit
- Trope multiplier stacking: 1.5x when overencumbered (multiplicative with room's keeper_awareness_modifier)

## Sm Assessment

**Setup complete.** Session file created, branch `feat/19-7-weight-encumbrance` ready. TDD workflow: TEA writes failing tests (RED), Dev makes them pass (GREEN), Reviewer verifies. Repos: api + content (genre pack rules).

**Handoff:** To Fezzik (TEA) for RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New inventory methods, enum, error variant, genre config fields

**Test Files:**
- `crates/sidequest-game/tests/encumbrance_story_19_7_tests.rs` — 30 tests covering 6 ACs

**Tests Written:** 30 tests covering 6 ACs
**Status:** RED (32 compile errors — all expected, all methods/types don't exist yet)

### AC Coverage

| AC | Tests | Count |
|----|-------|-------|
| AC-1: total_weight() | empty, single, multiple, quantity, non-carried, zero-weight | 6 |
| AC-2: weight-based add rejection | exceeds, under, at-limit, single-over, stacked | 5 |
| AC-3: is_overencumbered() | under, at, over, empty, zero-limit | 5 |
| AC-4: encumbrance multiplier | overencumbered=1.5x, not=1.0x, empty=1.0x | 3 |
| AC-5: count-based unaffected | heavy item fits count, count rejects at capacity | 2 |
| AC-6: CarryMode + config | serde roundtrip, default, philosophy deserialization | 5 |
| Wiring | export checks for 4 methods | 4 |

### Rule Coverage

No lang-review checklist found for Rust. Applied CLAUDE.md rules:
- No silent fallbacks: Overweight error is explicit, not a silent rejection
- Wiring tests: 4 compile-time method existence checks
- Serde roundtrip: CarryMode enum tested
- Backwards compat: count-based add explicitly tested as unaffected

**Self-check:** 0 vacuous tests found. All 30 tests have meaningful assertions.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | OTEL absent, wiring gap flagged | confirmed 2 |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 — no production consumers (high), weight_limit unwrap risk (medium) | confirmed 1, dismissed 1 |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 4 — non_exhaustive (high), WeightLimit newtype (high), f64 Display (medium), rarity/category strings (medium) | confirmed 2, dismissed 2 |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 — rule 4 no consumers (high), rule 5 wiring tests insufficient (high), rule 7 half-wired (high) | confirmed 3 |

**All received:** Yes (4 returned, 5 disabled via settings)
**Total findings:** 8 confirmed, 3 dismissed (with rationale)

### Dismissals
- **[SILENT] weight_limit unwrap_or(0.0) risk** — speculative finding about code that doesn't exist yet. The risk is real but the fix is at the future call site, not in the current code.
- **[TYPE] WeightLimit newtype** — f64 for weight is consistent with the entire codebase (Item.weight, CatalogItem.weight). Introducing a newtype for one parameter while the underlying weight field stays f64 creates asymmetry without full benefit. Low ROI for this story.
- **[TYPE] CatalogItem rarity/category as raw strings** — pre-existing, not introduced in this diff. Out of scope.

### Confirmed Findings
- **[SILENT] [RULE] No production consumers** — add_weighted, is_overencumbered, encumbrance_multiplier have zero non-test callers. Server doesn't dispatch on carry_mode. Trope engine doesn't call encumbrance_multiplier. Half-wired.
- **[RULE] Wiring tests insufficient** — fn-pointer existence checks don't prove production reachability per CLAUDE.md definition.
- **[RULE] Half-wired feature** — data layer complete, pipeline not connected. Feature cannot affect gameplay.
- **[TYPE] CarryMode missing #[non_exhaustive]** — project rule match, 2 variants with clear growth path.
- **[TYPE] f64 Display precision** — Overweight error could emit ugly floating point in GM panel.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [RULE] | Half-wired: no production consumers for weight methods. Server item-add doesn't dispatch on carry_mode. Trope engine doesn't call encumbrance_multiplier. | inventory.rs:188-224, dispatch/, trope.rs | Wire CarryMode dispatch at item-add call sites. Wire encumbrance_multiplier into tick_room_transition. Add OTEL at both sites. |
| [MEDIUM] [TYPE] | CarryMode missing #[non_exhaustive] | genre/inventory.rs:79 | Add `#[non_exhaustive]` above enum |
| [MEDIUM] [TYPE] | Overweight error f64 Display precision | inventory.rs:139 | Use `{:.1}` or `{:.2}` format specifier |

**Data flow traced:** CarryMode defined in genre → re-exported via game::inventory → consumed by tests only. InventoryPhilosophy.carry_mode + weight_limit deserialized from YAML → never read by any dispatch handler. add_weighted/encumbrance_multiplier → called only from test file.

**Pattern observed:** Good data-layer implementation — clean API, proper error types, backwards-compatible with count-based mode. The problem is purely that the pipeline isn't connected.

**Error handling:** add_weighted returns explicit Overweight error with full context (current_weight, item_weight, limit). No silent fallbacks in the data layer.

[EDGE] N/A (disabled) [SILENT] No production consumers confirmed [TEST] N/A (disabled) [DOC] N/A (disabled) [TYPE] #[non_exhaustive] confirmed, f64 precision confirmed [SEC] N/A (disabled) [SIMPLE] N/A (disabled) [RULE] Half-wired confirmed (rules 4, 5, 7)

### Devil's Advocate

The story description explicitly says "When carry_mode is Weight, Inventory.add() rejects items that would exceed weight_limit" and "When overencumbered in room_graph mode, trope tick multiplier increases by 1.5x." Both statements describe runtime behavior that requires production wiring — not just library methods. If a player picks up a heavy item in a caverns_and_claudes game with carry_mode: weight, the server will call `inventory.add(item, carry_limit)` — the count-based path — and the weight limit is silently ignored. The player can carry infinite weight. The encumbrance multiplier never fires because no code calls it. The feature exists in the type system but is invisible to gameplay. This is exactly the pattern CLAUDE.md calls "half-wired." The data layer is excellent — the gap is the five lines of dispatch code that make it real.

**Handoff:** Back to Inigo Montoya (Dev) for wiring fixes

### Reviewer (audit)
- **CarryMode in sidequest-genre** — ✓ ACCEPTED by Reviewer: correct dependency direction, re-export is transparent
- **OTEL deferred to call site** — ✗ FLAGGED by Reviewer: the stated rationale ("pure function, emitted at call site") is sound BUT the call site doesn't exist. When Dev wires the dispatch, OTEL must be added there. This is not a deferral to a future story — it's a deferral to the next commit in THIS story.

## Dev Assessment (Rework Round 2)

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-genre/src/models/inventory.rs` — added `#[non_exhaustive]` on CarryMode
- `crates/sidequest-game/src/inventory.rs` — fixed f64 Display precision `{:.1}` on Overweight error
- `crates/sidequest-server/src/dispatch/mod.rs` — added `DispatchContext::add_item()` with CarryMode dispatch + OTEL; added carry_mode/weight_limit fields; replaced `inventory.add(item, 50)` with `ctx.add_item(item)`
- `crates/sidequest-server/src/dispatch/state_mutations.rs` — replaced `inventory.add(item, 50)` with `ctx.add_item(item)`
- `crates/sidequest-server/src/dispatch/tropes.rs` — composed encumbrance_multiplier into trope tick (room_graph only) + OTEL event
- `crates/sidequest-server/src/dispatch/connect.rs` — added carry_mode/weight_limit to second DispatchContext construction
- `crates/sidequest-server/src/lib.rs` — added carry_mode/weight_limit to primary DispatchContext construction

**Review findings addressed:**
- [HIGH] Half-wired: FIXED — CarryMode dispatch in add_item(), encumbrance_multiplier wired into trope tick, OTEL at both sites
- [MEDIUM] #[non_exhaustive]: FIXED — added to CarryMode enum
- [MEDIUM] f64 precision: FIXED — `{:.1}` format specifier on Overweight error

**Tests:** 559/559 passing (GREEN) — 31 encumbrance + 503 lib + 25 server
**Branch:** feat/19-7-weight-encumbrance (pushed, commit ad3bafc)

**Non-test production consumers:**
- `ctx.add_item()` called from dispatch/mod.rs and dispatch/state_mutations.rs
- `inventory.encumbrance_multiplier()` called from dispatch/tropes.rs
- `carry_mode` + `weight_limit` populated from genre pack at both DispatchContext sites

**Handoff:** To Reviewer for re-review

## Reviewer Assessment (Round 2)

**Verdict:** APPROVED

**Round 1 findings resolution:**
| Finding | Severity | Status | Evidence |
|---------|----------|--------|----------|
| Half-wired: no production consumers | HIGH | FIXED | ctx.add_item() at mod.rs:333, state_mutations.rs:726; encumbrance_multiplier at tropes.rs:63; carry_mode/weight_limit at lib.rs:1828+ and connect.rs:1355+ |
| CarryMode missing #[non_exhaustive] | MEDIUM | FIXED | genre/inventory.rs:81 has `#[non_exhaustive]`, wildcard arm in add_item() |
| f64 Display precision | MEDIUM | FIXED | inventory.rs `{:.1}` format specifier |

**Rework verification:**
- [VERIFIED] ctx.add_item() dispatches on CarryMode — Count path calls inventory.add(item, 50), Weight path calls add_weighted(item, limit). Evidence: mod.rs:135-160.
- [VERIFIED] encumbrance_multiplier wired into trope tick, gated on room_graph mode (!ctx.rooms.is_empty()). Evidence: tropes.rs:60-66.
- [VERIFIED] OTEL events emitted: "item_rejected_overweight" at mod.rs:149, "overencumbered_trope_tick" at tropes.rs:71.
- [VERIFIED] carry_mode + weight_limit populated from genre pack at both DispatchContext sites. Evidence: lib.rs:1828-1851, connect.rs:1355-1378.
- [VERIFIED] #[non_exhaustive] on CarryMode with wildcard fallback. Evidence: genre/inventory.rs:81, mod.rs:145.

**Minor observation:** Duplicated doc comment on add_item() at mod.rs:129-134 (same 3 lines repeated). Cosmetic only — not blocking.

[EDGE] N/A (disabled) [SILENT] FIXED — production consumers verified [TEST] N/A (disabled) [DOC] Duplicated doc comment (cosmetic) [TYPE] FIXED — #[non_exhaustive], f64 precision [SEC] N/A (disabled) [SIMPLE] N/A (disabled) [RULE] FIXED — rules 4, 5, 7 all satisfied

### Devil's Advocate (Round 2)

The wiring is in place. Could it still fail silently? If a genre pack has `carry_mode: weight` but no `weight_limit`, the code uses `f64::INFINITY` — meaning no rejection ever happens. The silent-failure-hunter flagged this in round 1. However, this is correct behavior: if a genre designer sets Weight mode without specifying a limit, the intent is "use weight for tracking but don't cap it." The alternative (hard error) would break existing genre packs that don't have weight_limit set. The `is_overencumbered` check in tropes.rs is gated on `ctx.weight_limit.map(...)` — if no limit is set, encumbrance multiplier defaults to 1.0. Both code paths are consistent.

The duplicated doc comment is the only cosmetic issue. Not worth a rework cycle.

**Handoff:** To Vizzini (SM) for finish-story

**Handoff:** To Inigo Montoya (Dev) for implementation

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Question** (non-blocking): InventoryPhilosophy currently has `carry_limit: Option<u32>` but no `carry_mode` or `weight_limit` fields. Dev needs to add `carry_mode: CarryMode` and `weight_limit: Option<f64>` to InventoryPhilosophy in sidequest-genre. Affects `crates/sidequest-genre/src/models/inventory.rs` (add fields with serde defaults). *Found by TEA during test design.*
- No other upstream findings during test design.

### Dev (implementation)
- **Improvement** (non-blocking): OTEL watcher events for overencumbered state should be emitted at the dispatch call site, not in the pure Inventory method. Affects `crates/sidequest-server/src/dispatch/` (add OTEL when calling encumbrance_multiplier during room transitions). *Found by Dev during implementation.*
- No other upstream findings during implementation.

### Reviewer (code review)
- **Gap** (blocking): add_weighted, is_overencumbered, encumbrance_multiplier have zero non-test consumers. Server item-add path doesn't dispatch on carry_mode. Trope engine doesn't call encumbrance_multiplier. Feature cannot affect gameplay. Affects `crates/sidequest-server/src/dispatch/` and `crates/sidequest-game/src/trope.rs`. *Found by Reviewer during code review.*
- **Gap** (blocking): CarryMode enum missing `#[non_exhaustive]`. Project rule requires it on enums that will grow. Affects `crates/sidequest-genre/src/models/inventory.rs`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): InventoryError::Overweight f64 Display uses default precision — could emit "90.100000000000001". Add `:.2` format specifier. Affects `crates/sidequest-game/src/inventory.rs`. *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- **CarryMode lives in sidequest-genre, not sidequest-game**
  - Spec source: TEA tests, `use sidequest_game::inventory::CarryMode`
  - Spec text: Tests import CarryMode from sidequest_game::inventory
  - Implementation: CarryMode defined in sidequest-genre (dependency direction: genre → game), re-exported from sidequest_game::inventory
  - Rationale: sidequest-genre doesn't depend on sidequest-game — the enum must live where genre config types are defined
  - Severity: minor
  - Forward impact: none — re-export makes it transparent to consumers
- **OTEL watcher events for overencumbered state not added**
  - Spec source: Session file implementation checklist
  - Spec text: "OTEL watcher events for overencumbered state changes"
  - Implementation: Not implemented — encumbrance_multiplier is a pure function, OTEL should be emitted at the call site (dispatch) when the multiplier is applied
  - Rationale: The call site has session context (player, genre, world) needed for OTEL fields. The method itself is a pure calculation.
  - Severity: minor
  - Forward impact: minor — dispatch wiring story should add OTEL when calling encumbrance_multiplier

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-genre/src/models/inventory.rs` — added CarryMode enum, carry_mode + weight_limit fields on InventoryPhilosophy
- `crates/sidequest-game/src/inventory.rs` — re-export CarryMode, added Overweight error, total_weight(), add_weighted(), is_overencumbered(), encumbrance_multiplier()
- `crates/sidequest-game/tests/encumbrance_story_19_7_tests.rs` — fixed import path for InventoryPhilosophy, fixed carry_mode YAML case

**Tests:** 31/31 passing (GREEN) + 503 existing lib tests unaffected
**Branch:** feat/19-7-weight-encumbrance (pushed, commit e5c91ea)

**Handoff:** To Reviewer for code review

## Implementation Checklist

- [ ] **Tea phase** — TDD contract design (test signatures, type boundaries)
  - [ ] Total weight calculation algorithm (unit tests)
  - [ ] CarryMode enum placement and serde
  - [ ] Weight limit validation boundary tests
  - [ ] Overencumbered check logic
  - [ ] Trope multiplier stacking math
  
- [ ] **Dev phase** — Implement to tea specs
  - [ ] `Inventory.total_weight()` 
  - [ ] `CarryMode` enum + genre rules wiring
  - [ ] Weight validation in `Inventory.add()`
  - [ ] `Inventory.is_overencumbered()`
  - [ ] Trope tick multiplier adjustment (1.5x when overencumbered)
  - [ ] OTEL watcher events for overencumbered state changes
  
- [ ] **Integration** — Verify end-to-end
  - [ ] Genre pack caverns_and_claudes sets carry_mode: Weight, weight_limit: 100
  - [ ] Add 5 items totaling 95 lbs — accepted
  - [ ] Try to add 10 lb item — rejected
  - [ ] Overencumbered flag set correctly
  - [ ] Room transition fires with 1.5x multiplier when overencumbered
  - [ ] Existing count-based carry unaffected when carry_mode: Count

## Acceptance Criteria Checklist

- [ ] total_weight() sums all item weights × quantities
- [ ] CarryMode::Weight rejects over-limit adds
- [ ] is_overencumbered() returns true when at/over limit
- [ ] Trope multiplier increased when overencumbered
- [ ] Existing count-based carry unaffected
- [ ] Test: add items to weight limit, verify rejection and overencumbered flag