---
story_id: "26-3"
jira_key: "none"
epic: "26"
workflow: "trivial"
---
# Story 26-3: Wire session_restore into dispatch_connect

## Story Details
- **ID:** 26-3
- **Jira Key:** none (personal project)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-06T17:53:01Z
**Round-Trip Count:** 1
**Phase Completed:** 2026-04-06T13:50:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-06T13:35:00Z | 2026-04-06T13:50:00Z | 15m |

## Story Context

Epic 26 (Wiring Audit Remediation) discovered that `session_restore::extract_character_state()` 
is fully implemented with complete tests in `session_restore_story_18_9_tests.rs`, but never 
wired into the `dispatch_connect()` handler in `sidequest-server`.

**Current bug:** When a returning player reconnects, dispatch_connect manually extracts 
only hp, max_hp, level, xp from the saved character. Inventory and known_facts are skipped, 
defaulting to empty. Next auto-save overwrites the real inventory with empty. 
Players lose all items on reconnect (story 18-9 RED phase bug).

**Fix:** Replace the manual extraction in dispatch_connect with a call to 
`session_restore::extract_character_state()` to ensure ALL character state is restored.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | Pre-existing failures only (watcher_3_6, lore_15_10), 172 tests pass, 0 new failures | N/A — no new issues |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 — serde_json::to_value failure silently degrades character_json to None | confirmed 1 |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 3 — NonBlankString widening (medium), all-pub fields (medium), primitive obsession (low) | confirmed 1, dismissed 2 |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 — missing wiring test (rule 5), known_facts half-wired (rule 7) | confirmed 1, dismissed 1 |

**All received:** Yes (4 returned, 5 disabled via settings) — Round 1

### Round 2 Subagent Results (Rework Review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | Skipped | Rework — targeted verification | N/A |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | Rework — verified fix directly | N/A |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | Skipped | Rework — verified fix directly | N/A |
| 7 | reviewer-security | Yes | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | Skipped | Rework — verified fix directly | N/A |

**All received:** Yes (rework review — direct verification of 3 targeted fixes)
**Total findings:** 3 confirmed, 3 dismissed (with rationale)

### Dismissals
- **[TYPE] all-pub fields on RestoredCharacterState** — internal DTO consumed at a single call site within the same crate. No security boundary or invariant enforcement needed. Private fields + accessors would be over-engineering for a struct that exists only to shuttle data from extract to dispatch.
- **[TYPE] primitive obsession (hp/max_hp/ac as i32)** — matches CreatureCore field types. No VitalStats newtype exists in the codebase. Low confidence finding.
- **[RULE] known_facts half-wired (rule 7)** — known_facts survive via `*snapshot = saved.snapshot.clone()` (line 154), and downstream consumers (prompt.rs:288, mod.rs:2145) read them from character_json, not from a separate variable. The extraction in RestoredCharacterState serves OTEL telemetry (facts_count). Removing the field or adding a separate parameter would be churn — the data flow is complete via snapshot + character_json.

### Confirmed Findings
- **[SILENT] serde_json::to_value failure** — session_restore.rs:41-49 logs error but returns Some with character_json: None. Downstream: prompt.rs loses known_facts injection, PlayerState loses character_json. This is a silent fallback violating project rules.
- **[TYPE] NonBlankString→String widening** — session_restore.rs:53 calls .as_str().to_string() on a NonBlankString, losing the type invariant. Should clone NonBlankString directly.
- **[RULE] Missing wiring test** — No test verifies dispatch_connect calls extract_character_state and writes results into mutable stores.

## Reviewer Assessment (Round 2)

**Verdict:** APPROVED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [SILENT] | serde_json::to_value failure silently degrades character_json to None — narrator loses all known_facts, multiplayer PlayerState incomplete | session_restore.rs:41-49 | Return None on serialization failure so dispatch_connect treats it as corrupted save and returns error_response |
| [MEDIUM] [TYPE] | NonBlankString→String widening loses type invariant | session_restore.rs:53 | Use `character.core.name.clone()` and type the field as NonBlankString |
| [LOW] [RULE] | No wiring test for dispatch_connect → extract_character_state | tests/ | Add integration test that calls dispatch_connect with a saved snapshot and asserts mutable stores are populated |

**Data flow traced:** Saved snapshot → extract_character_state → restored fields written to dispatch-loop stores → character_json consumed by prompt.rs (known_facts injection) and shared_session PlayerState (multiplayer). The None path for character_json breaks both consumers silently.

**Pattern observed:** Good pattern — replacing inline extraction with a dedicated function that captures all fields. OTEL telemetry properly emits all restored state.

**Error handling:** None arm (connect.rs:137-144) correctly fails loud with error_response. BUT the serde failure path (session_restore.rs:41-49) silently continues — this is the blocking issue.

[EDGE] N/A (disabled) [SILENT] serde failure silent degradation confirmed [TEST] N/A (disabled) [DOC] N/A (disabled) [TYPE] NonBlankString widening confirmed [SEC] N/A (disabled) [SIMPLE] N/A (disabled) [RULE] Missing wiring test confirmed, known_facts wiring dismissed

**Round 1 findings resolution:**
| Finding | Severity | Status | Evidence |
|---------|----------|--------|----------|
| serde failure silent fallback | HIGH | FIXED | session_restore.rs:51 `return None` on Err, field now `serde_json::Value` (non-optional) |
| NonBlankString→String widening | MEDIUM | FIXED | session_restore.rs:16 `pub character_name: NonBlankString`, line 56 `.clone()` |
| Missing wiring test | LOW | DEFERRED | Logged as deviation with rationale (55-param function). Acceptable. |

**Rework verification:**
- [VERIFIED] serde failure → `return None` → dispatch_connect returns error_response. No silent fallback. Evidence: session_restore.rs:51, connect.rs:144.
- [VERIFIED] character_json is `serde_json::Value` (non-optional). Type system enforces presence. Evidence: session_restore.rs:33.
- [VERIFIED] character_name is `NonBlankString`. Converted to String only at consumption point (connect.rs:108). Evidence: session_restore.rs:16,56.
- [VERIFIED] Tests updated for new types: `.is_object()` replaces `.is_some()`, `.as_str()` for comparisons. 15/15 green. Evidence: tests lines 432, 438, 421, 490, 499.

**Data flow traced:** Saved snapshot → extract_character_state → Some(restored) with guaranteed character_json → dispatch stores populated → character_json consumed by prompt.rs and PlayerState. On serde failure: None → dispatch returns error_response to client. No silent degradation path.
**Pattern observed:** Good — fail-loud on corruption, type invariants preserved across boundaries.
**Error handling:** Both None paths (missing character, serde failure) return error_response. No silent fallbacks.

[EDGE] N/A (disabled) [SILENT] FIXED — verified return None [TEST] N/A (disabled) [DOC] N/A (disabled) [TYPE] FIXED — NonBlankString preserved [SEC] N/A (disabled) [SIMPLE] N/A (disabled) [RULE] wiring test deferred with proper deviation log

**Handoff:** To Vizzini (SM) for finish-story

### Devil's Advocate (Round 2)

The serde failure path now returns None, which is good. But what if the error_response message "Saved game corrupted: no character data found" is misleading? The actual cause was serialization failure, not missing character data. A player seeing this error would try to start fresh, but the save file is actually intact — it just has a character struct that serde can't round-trip. The error message conflates two different failure modes (no characters vs. unserializable character) under one message. This is a UX annoyance, not a correctness bug — the save is protected (not overwritten), and the player can reconnect. Low severity.

The NonBlankString conversion at connect.rs:108 (`as_str().to_string()`) creates a new allocation. This happens once per reconnect, so no performance concern. If `character_name_store` were ever changed to `Option<NonBlankString>`, the allocation could be avoided — but that's a broader refactor.

Neither of these rises to blocking severity.

### Devil's Advocate (Round 1, preserved)

What if a Character has a field that serializes on write but fails on read-back? `to_value()` serializes the full Character struct — if any field added later implements Serialize incorrectly or panics during serialization, the current path silently proceeds with a None character_json. The character "appears" restored — HP, inventory, name all correct — but the prompt context silently loses all known_facts and the multiplayer PlayerState has no character_json. The narrator then has amnesia about everything the character learned.

In a mystery/scenario game (Epic 7), this would be catastrophic: the player solved half the clues, reconnects, and the narrator has no idea what they know. The error log message exists, but it's a tracing::error buried in server output while the player wonders why the narrator forgot everything. No OTEL watcher event is emitted for this failure, so the GM panel can't detect it either. The user specifically confirmed: "it should error and not return a stub." Returning Some with character_json: None IS a stub value masquerading as a successful restore.

Additionally, the missing wiring test means if someone refactors dispatch_connect to use a different restore path, no test catches the regression. The unit tests for extract_character_state prove the function works in isolation, but nothing proves dispatch_connect calls it. This is exactly the "verify wiring, not just existence" principle — and the test suite doesn't satisfy it.

## Dev Assessment

**Implementation Complete:** Yes (rework round 1)
**Files Changed:**
- `crates/sidequest-game/src/session_restore.rs` — serde failure now returns None (fail loud); character_name typed as NonBlankString; character_json now non-optional serde_json::Value
- `crates/sidequest-game/tests/session_restore_story_18_9_tests.rs` — updated assertions for non-optional character_json and NonBlankString character_name
- `crates/sidequest-server/src/dispatch/connect.rs` — wrap character_json in Some() for Option<Value> store; convert NonBlankString to String at call site

**Tests:** 56/56 passing (GREEN)
- session_restore_story_18_9_tests: 15/15
- canonical_snapshot_story_15_8_tests: 16/16
- server_story_2_1_tests: 25/25

**Branch:** feat/26-3-wire-session-restore (pushed, commit 59d9af2)

**Review findings addressed:**
- [HIGH] serde failure: now returns None → dispatch_connect returns error_response. FIXED.
- [MEDIUM] NonBlankString: character_name field now NonBlankString, cloned directly. FIXED.
- [LOW] Wiring test: NOT ADDRESSED — dispatch_connect's 55-parameter signature makes a wiring test impractical without a test harness refactor (separate story scope).

**Handoff:** To Reviewer for re-review

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation, round 1)
- Session restore correctly restored hp, max_hp, level, xp, inventory, and known_facts
- OTEL telemetry emitted for GM panel verification
- Branch: feat/26-3-wire-session-restore (commit 47ce2a7)

### Dev (rework, round 2)
- **Improvement** (non-blocking): dispatch_connect has a 55-parameter signature making wiring tests impractical. Affects `crates/sidequest-server/src/dispatch/connect.rs` (needs test harness refactor — separate story). *Found by Dev during rework.*
- No other upstream findings during rework.

### Reviewer (code review)
- **Gap** (blocking): session_restore.rs:41-49 serde_json::to_value failure returns Some with character_json: None. Violates "No Silent Fallbacks." Must return None to trigger error_response path. Affects `crates/sidequest-game/src/session_restore.rs` (change error handling to propagate failure).
- **Improvement** (non-blocking): session_restore.rs:53 widens NonBlankString to String. Affects `crates/sidequest-game/src/session_restore.rs` (keep NonBlankString type on character_name field).
- **Gap** (non-blocking): No wiring integration test for dispatch_connect → extract_character_state. Affects `crates/sidequest-server/tests/` (add wiring test).

## Design Deviations

None — this is a straightforward wiring task.

### Reviewer (audit)
No deviations documented by Dev. No undocumented deviations found — the implementation correctly follows the "wire up what exists" pattern.

### Dev (implementation)
- **Wiring test not added (LOW finding deferred)**
  - Spec source: Reviewer Assessment, [LOW] finding
  - Spec text: "Add integration test that calls dispatch_connect with a saved snapshot and asserts mutable stores are populated"
  - Implementation: Not implemented — dispatch_connect has 55 parameters, no test harness exists
  - Rationale: Creating a test harness for a 55-parameter function is a refactoring task beyond this wiring story's scope
  - Severity: minor
  - Forward impact: none — existing 56 tests cover session_restore extraction and server lifecycle

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->