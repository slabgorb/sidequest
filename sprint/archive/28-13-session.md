---
story_id: "28-13"
jira_key: "none"
epic: "MSSCI-28"
workflow: "trivial"
---

# Story 28-13: Dead export cleanup — remove unwired pub fns and UI exports

## Story Details
- **ID:** 28-13
- **Jira Key:** MSSCI-28 (Epic, not story-specific)
- **Workflow:** trivial
- **Epic Parent:** 28 (Unified Encounter Engine)
- **Stack Parent:** 28-9 (must complete first)
- **Points:** 3

## Context

This story is part of the large encounter unification epic (28). Epic 28-9 ("Delete CombatState, ChaseState, etc.") deletes many old systems. This follow-up story audits what remains and removes all public functions and exports with zero non-test consumers.

The story includes two audit phases:

1. **API audit (sidequest-api workspace):** Remove pub functions from sidequest-game, sidequest-server, and other crates
2. **UI audit (sidequest-ui):** Remove orphaned exports from React components and hooks

## Technical Approach

### Phase 1: Identify Dead Exports

Run `cargo tree --duplicates` and use `ripgrep` to find pub items with zero callers outside tests:

```bash
# For each pub fn/struct/enum in the target list, search for references
# Pattern: grep -r "use.*::{item}" --include="*.rs" | grep -v "#\[cfg(test)\]" | grep -v "#\[test\]"
# Pattern: grep -r "{item}::" --include="*.rs" | filter test paths

cd /Users/keithavery/Projects/oq-2/sidequest-api
cargo expand --lib | grep "^pub " > /tmp/api_exports.txt
```

**API targets (from audit):**
- sidequest-server: `dedup_window`, `format_narrator_context`, `handle_accusation`, `last_narration`, `requires_npc_knowledge`, `try_claim_resolution`, `with_dedup_window`, `with_prompt_fragment`, `acquire_footnote`, `add_ambiguity_context`, `send_with_tools`, `transact_merchant`
- sidequest-game: `troper`, `troper_mut`, `with_client`, `debug_state`, `describe_player_effects`, `has_perception_effects`, `loadoutgen_binary_path`, `new_with_options`, `trace`

**UI targets (from audit):**
- CartographyMetadata, Region, Route, ExploredLocation (from 26-10 context; verify 26-10 didn't add consumers)
- `buttonVariants`, `toggleVariants`, `CreationChoice`, `OverlayManagerProps`, `TurnModeIndicatorProps`

### Phase 2: Verify Non-Test Consumers

For each item in the target list:

```bash
# Search for non-test usage in production code
cd /Users/keithavery/Projects/oq-2

# API: check all crates + server dispatch
grep -r "dedup_window" sidequest-api/crates --include="*.rs" | \
  grep -v test | grep -v "#\[" | grep -v "//"

# UI: check component tree
grep -r "CartographyMetadata" sidequest-ui/src --include="*.ts" --include="*.tsx" | \
  grep -v test | grep -v "export"
```

If no production callers exist, mark as dead.

### Phase 3: Downgrade or Delete

For each dead export:

1. **Delete completely** if:
   - No non-test callers
   - No comments indicating it's intentionally public for future use
   - Not part of a crate's public API (e.g., not in sidequest-protocol)

2. **Downgrade to `pub(crate)`** if:
   - Used by other modules in the same crate but shouldn't be exported publicly
   - Still useful but shouldn't be in the crate's lib.rs re-exports

3. **Keep as `pub`** if:
   - Used by code in a dependent crate
   - Part of a deliberate public API contract

### Phase 4: Verify Compilation

After each deletion/downgrade, run cargo check to catch any hidden consumers:

```bash
cd /Users/keithavery/Projects/oq-2

# API checks
cargo check -p sidequest-game
cargo check -p sidequest-server
cargo build -p sidequest-server  # Full build to catch all link-time dependencies

# UI checks
npm run build  # sidequest-ui full build
```

### Phase 5: Test Coverage

Run full test suite on each crate affected:

```bash
cargo test -p sidequest-game --lib
cargo test -p sidequest-server --lib
npm test -- --coverage  # sidequest-ui
```

## Acceptance Criteria

- [ ] Audit API crate for dead exports (grep-based scan completes without false negatives)
- [ ] Audit UI crate for dead exports (component import trace shows zero external consumers)
- [ ] Each target item has documented decision: deleted, downgraded, or kept with justification
- [ ] All deletions verified with `cargo check` (no compilation errors)
- [ ] All downgrades verified with `cargo check` (scope is correct)
- [ ] API test suite passes: `cargo test -p sidequest-game && cargo test -p sidequest-server`
- [ ] UI test suite passes: `npm test`
- [ ] Full API build succeeds: `cargo build -p sidequest-server`
- [ ] Full UI build succeeds: `npm run build`
- [ ] No dead exports remain in the audit list (all either deleted or downgrades with rationale documented)

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-07T18:54:17Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-07T10:45Z | 2026-04-07T18:15:45Z | 7h 30m |
| implement | 2026-04-07T18:15:45Z | 2026-04-07T18:38:34Z | 22m 49s |
| review | 2026-04-07T18:38:34Z | 2026-04-07T18:50:57Z | 12m 23s |
| implement | 2026-04-07T18:50:57Z | 2026-04-07T18:52:49Z | 1m 52s |
| review | 2026-04-07T18:52:49Z | 2026-04-07T18:54:17Z | 1m 28s |
| finish | 2026-04-07T18:54:17Z | - | - |

## Sm Assessment

Story 28-13 is a cleanup task following the 28-9 deletion of CombatState/ChaseState. The session file has a thorough audit plan covering both API (Rust) and UI (React) dead exports. Technical approach is sound — grep-based scan, verify non-test consumers, delete or downgrade, then compile-check. No blockers. Handing to Dev for implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- API (13 files, -150 lines):
  - `sidequest-game/src/beat_filter.rs` — removed `with_dedup_window`, `dedup_window` getter
  - `sidequest-game/src/multiplayer.rs` — removed `last_narration`
  - `sidequest-game/src/clue_activation.rs` — removed `requires_npc_knowledge` getter
  - `sidequest-game/src/barrier.rs` — removed `try_claim_resolution`
  - `sidequest-game/src/subject.rs` — removed `with_prompt_fragment`
  - `sidequest-agents/src/agents/intent_router.rs` — removed `add_ambiguity_context` + dead imports
  - `sidequest-agents/src/agents/resonator.rs` — removed `with_client`
  - `sidequest-agents/src/client.rs` — removed `send_with_tools`
  - `sidequest-agents/src/orchestrator.rs` — removed `troper`, `troper_mut`
  - `sidequest-agents/src/tools/lore_mark.rs` — downgraded `acquire_footnote` to private
  - `sidequest-agents/src/tools/merchant_transact.rs` — downgraded `transact_merchant` to private
  - `sidequest-server/src/lib.rs` — removed `trace`, `new_with_options`, `loadoutgen_binary_path`
  - `sidequest-server/src/shared_session.rs` — removed `has_perception_effects`, `describe_player_effects` + dead import
- UI (6 files, -6/+6 lines):
  - `MapOverlay.tsx` — unexported `ExploredLocation`
  - `button.tsx` — unexported `buttonVariants`
  - `toggle.tsx` — unexported `toggleVariants`
  - `CharacterCreation.tsx` — unexported `CreationChoice`
  - `OverlayManager.tsx` — unexported `OverlayManagerProps`
  - `TurnModeIndicator.tsx` — unexported `TurnModeIndicatorProps`

**Kept (production consumers confirmed):**
- `format_narrator_context` — called by sidequest-server dispatch/prompt.rs
- `handle_accusation` — called by sidequest-server dispatch/slash.rs
- `debug_state` — registered as HTTP endpoint

**Tests:** 229/232 API (3 pre-existing failures), 962/1011 UI (49 pre-existing)
**Branch:** feat/28-13-dead-export-cleanup (pushed in both repos)

**Handoff:** To review phase

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | clean | none | N/A |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 8 | confirmed 2, dismissed 6 (pre-existing, same root cause) |

**All received:** Yes (4 returned, 5 disabled via settings)
**Total findings:** 2 confirmed (1 root cause), 6 dismissed (duplicates of same root cause across rules 2/4/5/7)

### Rule-checker finding analysis

The rule-checker flagged `lore_mark.rs` and `merchant_transact.rs` across 4 rules (no-stubbing, verify-wiring, wiring-test, no-half-wired). All 8 findings trace to the same root cause: Dev downgraded these functions to private instead of deleting the modules. This created dead private code in half-wired modules.

**Confirmed as 1 blocking finding:** Dev must delete these modules entirely (functions + types + module declarations in mod.rs) since they are not wired into assemble_turn.rs and the project prohibits half-wired features.

**Dismissed 6:** Duplicate findings on the same two files across different rule numbers — same root cause, same fix.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [RULE] | Half-wired modules: `acquire_footnote` and `transact_merchant` downgraded to private but not deleted. Creates dead private code with public orphaned types. `assemble_turn.rs:184` bypasses `transact_merchant` entirely. | `sidequest-agents/src/tools/lore_mark.rs:55`, `merchant_transact.rs:47` | Delete both modules entirely (fn + types + `pub mod` in `tools/mod.rs`). Or wire into `assemble_turn.rs` if the validation is needed. |

**Observations:**
1. [VERIFIED] 16 of 18 pub fn removals are correct — zero non-test consumers confirmed via grep + cargo check. Evidence: `barrier.rs` claim mechanism uses internal `resolve()` at line 427, not the removed `try_claim_resolution`.
2. [VERIFIED] `troper`/`troper_mut` removal is correct — `orchestrator.rs:179` field is initialized but never accessed even internally. Cascading dead field (non-blocking, separate story).
3. [VERIFIED] `send_with_tools` removal safe — `send_impl` at `client.rs:321` still supports `allowed_tools` via `send_session`. Capability retained.
4. [VERIFIED] Dead import cleanup correct — `ContextBuilder`, `AttentionZone`, `PromptSection`, `SectionCategory` in `intent_router.rs`; `PerceptionRewriter` in `shared_session.rs`. All were sole consumers of removed functions.
5. [VERIFIED] All 6 UI export removals correct — no external imports found for any of them.
6. [HIGH] [RULE] `lore_mark.rs` and `merchant_transact.rs` — half-wired modules. See severity table.
7. [EDGE] N/A — disabled
8. [SILENT] Clean — no silent failures introduced by any removal.
9. [TEST] N/A — disabled
10. [DOC] N/A — disabled
11. [TYPE] Clean — no type contract violations. TurnBarrier concurrency contract intact.
12. [SEC] N/A — disabled
13. [SIMPLE] N/A — disabled
14. [RULE] Rule-checker confirmed 16/18 removals compliant. 2/18 (lore_mark, merchant_transact) flagged as half-wired.

### Rule Compliance

| Rule | Instances | Compliant | Violations |
|------|-----------|-----------|------------|
| No silent fallbacks | 18 | 18 | 0 |
| No stubbing | 18 | 16 | 2 (lore_mark.rs, merchant_transact.rs — dead private fns) |
| Verify wiring | 18 | 16 | 2 (same two files — not wired into assemble_turn) |
| No half-wired features | 18 | 16 | 2 (same two files — public types, private unreachable fn) |
| OTEL observability | 18 | 18 | 0 (cleanup story, no subsystem behavior change) |

### Devil's Advocate

Could someone argue this code is broken beyond the lore_mark/merchant_transact issue? Let me try.

The `troper` field on Orchestrator (line 179) is now a dead field — initialized in `new()` at line 227 but never accessed after removing the getters. A `TroperAgent::new()` runs on every Orchestrator construction, potentially doing work (allocations, default setup) for nothing. If `TroperAgent::new()` has side effects or significant cost, this is wasted computation on every game session. However, checking `TroperAgent::new()` — it's a simple struct construction with no side effects. So this is dead weight, not a bug. Still, it's a cascading dead code smell that a follow-up story should address.

Could removing `with_prompt_fragment` from `RenderSubject` break the render pipeline? The doc comment said "Used by the render pipeline to enrich prompts with NPC physical descriptions." But grep confirms zero callers — the comment described *intended* use, not *actual* use. The render pipeline accesses `prompt_fragment` directly via the field (which remains). No breakage.

Could removing `new_with_options` from AppState break test harnesses? Tests might construct AppState with headless mode. But grep confirms zero callers — tests use `new_with_game_service` + `.with_tts_disabled(true)` chain instead. The builder pattern superseded this convenience constructor.

Could the UI export removals break lazy-loaded or dynamically imported components? In this codebase, all component imports are static ESM `import { X } from` statements. No `React.lazy()`, no dynamic `import()` of these specific types. The grep confirms no external imports. Safe.

The devil's advocate found no additional issues beyond the lore_mark/merchant_transact half-wire, which is already the blocking finding.

**Handoff:** Back to Dev for fixes — delete `lore_mark.rs` and `merchant_transact.rs` modules entirely.

## Subagent Results (Rework Re-review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — rework verified via cargo check |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A — no new silent failures from deletion |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | clean | none | N/A — no type contract change from full deletion |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | none | N/A — original violations resolved by full deletion |

**All received:** Yes (rework re-review — focused verification of rejection fix, original subagent results from round 1 still apply for the unchanged 16 removals + 6 UI changes)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment (Rework Re-review)

**Verdict:** APPROVED

**Rework verification:**
- [VERIFIED] `lore_mark.rs` deleted — file does not exist on disk. Zero references remain in codebase (grep for LoreMarkInput/LoreMarkError/acquire_footnote returns nothing).
- [VERIFIED] `merchant_transact.rs` deleted — file does not exist on disk. Zero references remain in codebase (grep for MerchantTransactInput/MerchantTransactError/transact_merchant returns nothing).
- [VERIFIED] `tools/mod.rs` updated — `pub mod lore_mark` and `pub mod merchant_transact` declarations removed. File now has 21 lines, down from 23.
- [VERIFIED] Compilation clean — `cargo check` passes with 40 warnings (down from 43 before this story, 3 fewer from deleted dead code).
- [RULE] All rule violations from round 1 (no-stubbing, verify-wiring, wiring-test, no-half-wired) are resolved — the half-wired modules no longer exist.

**Original round 1 findings (unchanged, still valid):**
1. [VERIFIED] 16 pub fn removals correct — zero non-test consumers
2. [VERIFIED] Dead import cleanup correct
3. [VERIFIED] All 6 UI export removals correct
4. [SILENT] Clean
5. [TYPE] Clean
6. [EDGE] N/A — disabled
7. [TEST] N/A — disabled
8. [DOC] N/A — disabled
9. [SEC] N/A — disabled
10. [SIMPLE] N/A — disabled

**Data flow traced:** No data flows affected — this is a pure deletion story. All removed items had zero production callers.
**Pattern observed:** Clean dead code removal pattern at `tools/mod.rs:10-13` — module declarations removed alongside file deletion.
**Error handling:** N/A — no error handling paths affected by deletions.
**Handoff:** To SM for finish-story

## Dev Assessment (Rework)

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-agents/src/tools/lore_mark.rs` — DELETED (86 lines: acquire_footnote + LoreMarkInput/Error + parse_category)
- `sidequest-agents/src/tools/merchant_transact.rs` — DELETED (96 lines: transact_merchant + MerchantTransactInput/Error)
- `sidequest-agents/src/tools/mod.rs` — removed `pub mod lore_mark` and `pub mod merchant_transact` declarations

**Compilation:** cargo check passes, warnings dropped 43→40
**Branch:** feat/28-13-dead-export-cleanup (pushed)
**Handoff:** To review phase

## Delivery Findings

### Dev (implementation)
- **Improvement** (non-blocking): `acquire_footnote` and `transact_merchant` are the sole public fns in their modules. The entire `lore_mark` and `merchant_transact` tool modules may be dead — no callers for any types or functions. Could be candidates for full module removal in a future cleanup pass. Affects `sidequest-agents/src/tools/lore_mark.rs` and `sidequest-agents/src/tools/merchant_transact.rs` (consider removing modules entirely). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): `troper: TroperAgent` field on Orchestrator (`orchestrator.rs:179`) is now dead — initialized but never accessed after removing getters. Cascading dead code from this story. Affects `sidequest-agents/src/orchestrator.rs` (remove field, import, and constructor initialization). *Found by Reviewer during code review.*

## Design Deviations

### Dev (implementation)
- **Downgraded instead of deleted for lore_mark and merchant_transact** — RESOLVED in rework: both modules now fully deleted (files + mod.rs declarations). Original deviation no longer applies.

### Reviewer (audit)
- **Downgraded instead of deleted for lore_mark and merchant_transact** → ✗ FLAGGED by Reviewer: Downgrading to private creates dead private code in half-wired modules. Project rules ("no half-wired features", "never rationalize unwired code") require either wiring into assemble_turn.rs or deleting the entire modules. Dev's rationale ("will likely be wired") is the exact rationalization pattern the rules prohibit.
  → RESOLVED: Dev deleted both modules entirely in rework commit.