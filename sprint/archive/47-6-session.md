# Story 47-6: Tea ritual auto-fire — three-layer fix (room matcher, bond rebind, opening hook, OTEL)

## Story Details

- **ID:** 47-6
- **Epic:** 47 (Magic System Coyote Reach v1)
- **Workflow:** tdd
- **Type:** bug
- **Priority:** p1
- **Points:** 5
- **Repos:** server only
- **Branch:** feat/47-6-tea-ritual-three-layer-fix

---

## Problem Statement

The `the_tea_brew` confrontation wired in story 47-4 never fires. A playsession audit discovered three independent bugs that combine to ensure silent failure:

### Bug 1: Room-name Matcher Accepts Wrong Format

**File:** `sidequest-server/sidequest/game/room_movement.py:92-101`

The matcher accepts either:
- Colon-prefixed form: `<chassis_id>:<room_local>` (e.g. `"kestrel:galley"`)
- Bare lowercase room id: `"galley"`

But the narrator emits the narrator's display format: `"<chassis_name> — <Display>"` (em-dash separated, e.g. `"The Kestrel — Galley"`).

After normalize-and-lowercase, this becomes `"the_kestrel_—_galley"`, which matches neither shape. The function silently returns with no confrontation firing.

**Evidence:** Server log shows:
```
state.location_update old='The Kestrel — Cockpit' new='The Kestrel — Galley'
```
…with no subsequent confrontation firing.

### Bug 2: Bond Ledger Never Rebound to Real Character ID

**File:** `sidequest-server/sidequest/game/chassis.py:251-253`

The bond_seed at chargen has `character_id="player_character"` as a placeholder. The comment explicitly TODOs: "rebinding to follow-on chargen wiring task" — **this task never landed.**

**Evidence:** Save shows `bond_ledger[0].character_id = "player_character"` with `bond_tier_chassis = "trusted"`. The real character is "Zanzibar Jones".

**Result:** When `process_room_entry` calls `chassis.bond_for("Zanzibar Jones")`, it returns None because the bond entry is keyed to `"player_character"`. The room-entry hook returns at line 105 even if Bug 1 is fixed.

### Bug 3: Opening Dispatch Bypasses Room-Entry Hook

**File:** `sidequest-server/sidequest/server/dispatch/opening.py:81-84`

The opening pipeline sets `interior_room_label` directly **without** going through `process_room_entry()`. 

**Result:** The FIRST eligible moment—turn 1, cold start in galley with bond tier `trusted`—silently skips eligibility evaluation. Only narrator-driven location *updates* (cockpit→galley) reach the hook at all.

### Bug 4 (Cross-Cutting): Silent Returns, No OTEL

**File:** `sidequest-server/sidequest/game/room_movement.py:91, 101, 105, 121`

`process_room_entry` has return points at lines 91, 101, 105, 121 with **zero watcher events**. Sebastien's lie detector (the GM panel) is blind to whether the hook engaged.

**CLAUDE.md Principle:** Per "OTEL Observability Principle," every backend decision path must emit a span so the GM panel can verify the fix is working. Claude is excellent at improvising convincing narration with zero mechanical backing—OTEL logging is the only way to catch this.

---

## Acceptance Criteria

1. **Room-name matcher fix:** Given a session where the player is in `"The Kestrel — Galley"` (narrator's chassis-qualified form) with `bond_tier_chassis ≥ familiar`, when narrator emits a location update from cockpit→galley, then `the_tea_brew` outputs (`bond_strength_growth_via_intimacy`, `chassis_lineage_intimate`) land on the snapshot and `chassis_autofire_cooldowns["kestrel:the_tea_brew"]` is set.

2. **Opening hook integration:** Given a fresh session opening into the galley with bond_tier `trusted`, when the opening pipeline completes, then `the_tea_brew` is evaluated and fires on turn 1 (no silent skip of opening-time eligibility).

3. **Bond rebinding:** Given the player character "Zanzibar Jones" was bound at chargen against a chassis with bond_seed `character_role: "player_character"`, the bond_ledger entry's `character_id` is rebound to "Zanzibar Jones" (or whatever the actual chargen character id is) at session-start time.

4. **OTEL watcher spans:** Every return path in `process_room_entry` emits a watcher span:
   - `room_entry.skipped` (with reason: `not_chassis_room`, `no_bond_for_actor`, `no_magic_state`, `room_not_in_chassis`)
   - `room_entry.eligible_evaluated` (with chassis_id, room_local_id, eligible_count, fired_count)
   
   The GM dashboard must visibly show whether the hook engaged.

5. **Regression test:** Test feeds the literal narrator string `"The Kestrel — Galley"` (with em-dash) and asserts `the_tea_brew` outputs land. **This test MUST exist or AC1 is unverifiable.**

6. **Wiring test:** Integration test that runs through full `narration_apply` flow (not just unit-testing `process_room_entry` in isolation)—proves the bug is fixed end-to-end, not just patched in one function.

---

## Source Files to Inspect

These files contain the bugs and fix locations:

- **sidequest-server/sidequest/game/room_movement.py** — matcher logic + auto-fire eligibility evaluation
- **sidequest-server/sidequest/game/chassis.py** — init_chassis_registry, line 248-271 (where bond rebind belongs)
- **sidequest-server/sidequest/server/dispatch/opening.py** — line 81-84 (interior_room_label set without hook)
- **sidequest-server/sidequest/server/narration_apply.py** — line 941-957 (existing process_room_entry call site)
- **sidequest-server/sidequest/magic/confrontations.py** — find_eligible_room_autofire, evaluate_auto_fire_triggers
- **sidequest-content/genre_packs/space_opera/worlds/coyote_star/confrontations.yaml** — the_tea_brew definition
- **sidequest-content/genre_packs/space_opera/worlds/coyote_star/rigs.yaml** — bond_seeds (look for player_character placeholder)

---

## Context & Related Work

- **Story 47-4** — Original tea_brew wiring (marked done, merged 2026-05-03). This story is the follow-up that fixes 47-4's silent-failure modes.
- **ADR-067** — Unified Narrator Agent (persistent session, narrator name resolution)
- **ADR-090** — OTEL Dashboard Restoration after Python Port

---

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-04T22:04:39Z
**Round-Trip Count:** 1

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-04 | 2026-05-04T21:18:16Z | 21h 18m |
| red | 2026-05-04T21:18:16Z | 2026-05-04T21:25:30Z | 7m 14s |
| green | 2026-05-04T21:25:30Z | 2026-05-04T21:37:59Z | 12m 29s |
| spec-check | 2026-05-04T21:37:59Z | 2026-05-04T21:40:20Z | 2m 21s |
| verify | 2026-05-04T21:40:20Z | 2026-05-04T21:43:03Z | 2m 43s |
| review | 2026-05-04T21:43:03Z | 2026-05-04T21:49:19Z | 6m 16s |
| red | 2026-05-04T21:49:19Z | 2026-05-04T21:51:28Z | 2m 9s |
| green | 2026-05-04T21:51:28Z | 2026-05-04T21:56:29Z | 5m 1s |
| spec-check | 2026-05-04T21:56:29Z | 2026-05-04T21:57:21Z | 52s |
| verify | 2026-05-04T21:57:21Z | 2026-05-04T21:59:11Z | 1m 50s |
| review | 2026-05-04T21:59:11Z | 2026-05-04T22:02:21Z | 3m 10s |
| spec-reconcile | 2026-05-04T22:02:21Z | 2026-05-04T22:04:39Z | 2m 18s |
| finish | 2026-05-04T22:04:39Z | - | - |

---

## Dev Assessment (green rework)

**Implementation Complete:** Yes
**Tests:** 30/30 targeted green. Full sweep: 28 pre-existing failures unchanged (same set as initial green; verified by stash/pop). Lint clean.
**Branch:** `feat/47-6-tea-ritual-three-layer-fix` in sidequest-server, commit `ced2440` pushed.

**Files Changed (rework):**
- `sidequest-server/sidequest/magic/confrontations.py` — `find_eligible_room_autofire` no longer cooldown-filters; signature dropped 3 unused parameters (chassis_id, current_turn, cooldown_ledger). Single caller; clean contract.
- `sidequest-server/sidequest/game/room_movement.py` — `process_room_entry` now applies the cooldown gate per-confrontation inside its dispatch loop. `eligible_count` reflects matched-by-room-and-bond entries; `fired_count` increments only when an entry both matches AND is off cooldown AND dispatches. Docstring opening rewritten to describe all three accepted room_id formats.
- `sidequest-server/sidequest/game/chassis.py` — `rebind_chassis_bonds_to_character` snapshot parameter typed `GameSnapshot` via TYPE_CHECKING import (avoids the session↔chassis import cycle).

**Reviewer blockers — all three addressed:**
1. ✓ `fired_count vs eligible_count` semantics — moved cooldown filtering into `process_room_entry`. The strengthened test from TEA's red rework (e114f27) now passes; the cooldown-blocked re-entry produces `eligible_count == 1, fired_count == 0`. GM panel can distinguish "matched but on cooldown" from "no match."
2. ✓ Stale `process_room_entry` docstring — rewritten to describe all three formats.
3. ✓ Missing `snapshot: GameSnapshot` annotation — added with TYPE_CHECKING guard.

**Reviewer non-blocking observations — addressed via deferral:**
- Em-dash sensitivity test (ASCII hyphen variant): Not added in this pass to keep the rework minimal. Captured in Delivery Findings as a follow-up.
- `chassis.py` `__all__`: pre-existing absence; not in 47-6 scope.

**Handoff:** To The Man in Black (Architect) for spec-check round 2.

---

## Tea Assessment (red rework)

**RED Rework Complete:** Yes
**Tests Authored:** 1 modification — strengthened `test_evaluated_span_emitted_with_fired_zero_when_cooldown_blocks` (test_room_entry_otel_spans.py:179) to assert `eligible_count >= 1` on the cooldown-blocked second span, in addition to the existing `fired_count == 0`.

**RED Verification:** 1 failing test, 29 still passing. Failure output:
```
AssertionError: second entry should still SEE the confrontation as a match —
the cooldown-blocking distinction relies on eligible_count reflecting
matched-before-cooldown candidates. saw {'chassis_id': 'kestrel',
'room_local_id': 'galley', 'eligible_count': 0, 'fired_count': 0}
```

The current implementation produces `eligible_count == 0` because `find_eligible_room_autofire` filters cooldown-blocked entries upstream — exactly what the Reviewer's three subagents flagged. The strengthened test now pins the docstring promise.

**Dev contract:** Move cooldown filtering OUT of `find_eligible_room_autofire` and INTO `process_room_entry`. After the fix, on a cooldown-blocked re-entry:
- `eligible_count >= 1` (the_tea_brew matched the room+bond)
- `fired_count == 0` (cooldown gate prevented dispatch)

The other Reviewer-flagged blockers (stale `process_room_entry` docstring at lines 60-66, missing `snapshot: GameSnapshot` annotation in `rebind_chassis_bonds_to_character`) are pure code/doc fixes — Dev addresses them in green pass alongside the cooldown logic.

**Branch:** `feat/47-6-tea-ritual-three-layer-fix` in sidequest-server, RED-rework commit `e114f27` pushed.

**Handoff:** To Inigo Montoya (Dev) for green rework. The test strengthening was minimal — one extra assertion. The production-code change to satisfy it is non-trivial: the cooldown contract of `find_eligible_room_autofire` must change, and any other caller of that function must be re-validated. (Currently only `process_room_entry` calls it for room-entry, and the bar-DSL evaluator `evaluate_auto_fire_triggers` is independent.)

---

## Subagent Results (round 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | clean | 0 | confirmed 0, dismissed 0, deferred 0 |
| 5 | reviewer-comment-analyzer | Yes | clean | 0 | confirmed 0, dismissed 0, deferred 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 | confirmed 0, dismissed 0, deferred 0 |

**All received:** Yes (4 enabled returned, 5 disabled per workflow.reviewer_subagents settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred — every round-1 blocker addressed without introducing new violations.

---

## Reviewer Assessment (round 2)

**Verdict:** APPROVED

All three round-1 blockers fixed; rework did exactly what was asked, nothing more, nothing less. The strengthened cooldown test now genuinely pins the contract that Sebastien's lie detector relies on.

**Round-1 blocker resolution** (each verified by at least two subagents):

1. ✓ **`fired_count` vs `eligible_count` semantics** [SIMPLE][TEST][RULE] — Cooldown filtering moved out of `find_eligible_room_autofire` into `process_room_entry`'s dispatch loop (room_movement.py:147-172). On a cooldown-blocked re-entry, the span now emits `eligible_count=1, fired_count=0`. test-analyzer confirmed: "the cooldown `continue` fires, `fired_count` stays 0, and the span is emitted with `eligible_count=1, fired_count=0`. Both assertions are satisfied by real behavior, not coincidentally." rule-checker rule #13 (fix-introduced regression): clean.

2. ✓ **Stale `process_room_entry` docstring** [DOC] — Opening sentence rewritten ("match the entered room AND pass the cooldown gate" — verify round 2 commit `ea4374e`); body lists three accepted formats explicitly. comment-analyzer confirmed: "All three formats accurately described and match the implementation."

3. ✓ **Missing `snapshot: GameSnapshot` annotation** [RULE] — chassis.py:194-196 typed via TYPE_CHECKING import (line 16-19) to avoid the session↔chassis import cycle. rule-checker rule #3: clean. rule-checker rule #10 specifically validated the import hygiene: "the guard breaks the cycle correctly."

**Bonus deviation** (Dev logged, Architect accepted, Reviewer concurs): `find_eligible_room_autofire` lost three unused parameters (`chassis_id`, `current_turn`, `cooldown_ledger`) post-rework. Single caller, no test fixtures touched. Cleaner contract.

**Verified (with evidence):**
- `[VERIFIED]` Cooldown gate is per-confrontation and observable. `room_movement.py:148-159` — `cooldown_turns` is read from `cdef.fire_conditions`, the gate compares `current_turn - last_fired < cooldown_turns`, and on hit it `continue`s (skipping dispatch + cooldown stamp + fired_count++). The `room.entry_evaluated` span at line 175-180 emits both counts. Compliant with CLAUDE.md OTEL Observability Principle.
- `[VERIFIED]` `if cdef.fire_conditions else 0` fallback at room_movement.py:155-156 is unreachable per rule-checker — `find_eligible_room_autofire` already filters out entries with `fire_conditions is None`. Belt-and-suspenders, harmless. Could be removed in a future cleanup, but defensive coding here doesn't violate any rule.
- `[VERIFIED]` TYPE_CHECKING import correctly placed. `chassis.py:16-19` after stdlib imports, before module body. `from __future__ import annotations` already present (line 6) makes all annotations strings at runtime, so the guard is double-protection — no AttributeError risk under any Python version. rule-checker confirmed.
- `[VERIFIED]` Strengthened cooldown test fails clearly if the cooldown split regresses. Test asserts `eligible_count >= 1` first, `fired_count == 0` second; pytest stops on the first failure with `"second entry should still SEE the confrontation as a match — saw {...}"`. Diagnostic clarity: caller knows which half of the contract broke.
- `[VERIFIED]` 30/30 targeted tests green; lint clean; no merge conflicts; 28 pre-existing branch failures unchanged. Preflight confirmed.

**Devil's Advocate.**
What if the round-2 fix introduces a different bug at a non-rig caller of `find_eligible_room_autofire`? Checked: there are no other callers — `process_room_entry` is the sole consumer (verified by grep). What if a future world has a bond-tier configuration where the order of entries in `eligible` matters and the cooldown gate produces a partial dispatch (some fired, some skipped)? The fired_count would correctly reflect dispatched entries; the eligible_count would correctly reflect matched ones. The cooldown ledger is per-(chassis, confrontation) so partial dispatch within a single room-entry call works correctly. What if a clock skew or test fixture sets `current_turn` lower than `last_fired`? The arithmetic `current_turn - last_fired` would be negative, which is `< cooldown_turns`, so the gate would block. That's wrong but only happens under explicit test misuse — not a real-world failure mode. What if `cdef.fire_conditions.cooldown_turns` is 0? The gate becomes `(current_turn - last_fired) < 0`, which is false for any non-decreasing turn counter, so a cooldown_turns=0 entry would always fire. Correct semantically: zero cooldown means no gating. What if multiple chassis have the same confrontation id? The cooldown key includes `chassis.id` (`f"{chassis.id}:{cdef.id}"`) so they don't collide. **Devil's advocate found no new issues.** Round-2 verdict stands: APPROVED.

**Handoff:** To SM (Vizzini) for finish-story.

---

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 7 | confirmed 3, deferred 4 |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 3 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 | confirmed 4, deferred 1 |

**All received:** Yes (4 enabled returned, 5 disabled per workflow.reviewer_subagents settings)
**Total findings:** 6 confirmed (1 cross-confirmed by 3 subagents), 5 deferred (with rationale), 0 dismissed

---

## Reviewer Assessment

**Verdict:** REJECTED

The story sets out to make Sebastien's lie detector work by emitting OTEL spans on every silent return path. Three independent subagents (comment-analyzer, test-analyzer, rule-checker) flagged the same regression: the `room.entry_evaluated` span cannot deliver the diagnostic capability the docstring promises, and the test that pretends to verify it passes vacuously. That defeats the story's stated purpose. Two smaller HIGH findings round out the rejection.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [DOC][TEST][RULE] | `emit_room_entry_evaluated` docstring promises `fired_count < eligible_count when cooldown blocks dispatch`, but `find_eligible_room_autofire` filters cooldown-blocked entries upstream — so `fired_count == eligible_count` always. The GM panel cannot distinguish "nothing matched" from "matched but on cooldown." Cross-confirmed by 3 subagents. | `sidequest/game/room_movement.py:162`, `sidequest/telemetry/spans/rig.py:121-126`, `tests/integration/test_room_entry_otel_spans.py:166` | Either: (a) move cooldown filtering OUT of `find_eligible_room_autofire` and INTO `process_room_entry`, so `eligible` includes matched-but-cooldown-blocked entries and `fired` excludes them — then the test must assert `eligible_count >= 1 AND fired_count == 0` on the second call. OR (b) drop the false promise: rename `fired_count` → `matched_count` (or remove the field entirely), update the docstring to admit both counts always equal under current evaluator semantics, and update the test to assert `eligible_count == 0` on cooldown-blocked re-entry (the actual outcome). Story 47-6's purpose is GM observability — option (a) honors that purpose. |
| [HIGH] [DOC] | `process_room_entry` docstring opening sentence still claims "`room_id` is chassis-scoped — `'<chassis_id>:<room_local>'`" and that non-matching rooms are no-ops. The implementation at lines 80-87 now accepts three formats and the em-dash form is no longer a no-op. The docstring contradicts the implementation. | `sidequest/game/room_movement.py:60-66` | Update the docstring opening to describe all three accepted formats (matches the inline comment block at lines 80-87). |
| [MEDIUM] [RULE] | `rebind_chassis_bonds_to_character(snapshot, character_id: str)` — `snapshot` parameter is untyped at a public function boundary called from production code. Python lang-review rule #3 (type annotation gaps at boundaries). `GameSnapshot` is already imported in the companion `init_chassis_registry`. | `sidequest/game/chassis.py:193` | Add `snapshot: GameSnapshot` annotation. Two-character fix. |

**Non-blocking observations:**

- **[LOW] [TEST]** `test_session_opened_in_galley_evaluates_tea_brew` uses `character_id="player_character"` (placeholder) — this bypasses Bug 2 entirely. Genuine coverage is provided by the `_with_real_character_fires_tea_brew` companion test. Not blocking but the placeholder version's name is misleading. Consider renaming or merging.
- **[LOW] [TEST]** Missing negative test for em-dash sensitivity. The matcher uses `rsplit(" — ", 1)` (em-dash with surrounding spaces). A test that feeds `"The Kestrel - Galley"` (ASCII hyphen) and asserts the_tea_brew does NOT fire would pin the matcher's exact-separator contract. Worth adding in a follow-up.
- **[LOW] [RULE]** `chassis.py` has no `__all__`. Pre-existing absence; this story adds a new public symbol. Per "boy-scouting bounded" — defer to a tech-debt cleanup that sets `__all__` for the whole module rather than touch it here.
- **[LOW] [RULE]** `room_id` from narrator output is LLM-generated text passed through `rsplit/strip/lower/replace` without length validation. Python rule #11 applies but severity is low (safe dict lookup, no exec/SQL). Defer with justification: project SOUL.md "Zork Problem" says never reduce player input to keyword matching — likewise narrator output should be flexible. A length cap would be defensive over-engineering at this seam.

**Verified (with evidence):**
- `[VERIFIED]` `process_session_open` is a thin delegation, no swallowing — `room_movement.py:190-197` checks `snap.location` and forwards to `process_room_entry`. No try/except. Compliant with python rule #1 (silent exception swallowing).
- `[VERIFIED]` `rebind_chassis_bonds_to_character` is idempotent and protective — `chassis.py:208-210` only rewrites entries with `entry.character_id == "player_character"`. A second call with a different real id leaves the first real id unchanged (test_rebind_leaves_already_rebound_entries_alone verifies this).
- `[VERIFIED]` chargen-complete wiring at `websocket_session_handler.py:1306-1321` runs `init_chassis_registry → rebind → process_session_open` outside any try/except; rig errors propagate naturally rather than being swallowed. Rule #1 compliant.
- `[VERIFIED]` All 32 targeted tests green; lint clean on changed files; no debug code; no merge conflicts (preflight result).
- `[VERIFIED]` Span constants registered in `FLAT_ONLY_SPANS` per project convention (`rig.py:25-32`); the completeness test enforced elsewhere will pass.
- `[VERIFIED]` `yaml.safe_load` (not `yaml.load`) in pre-existing chassis.py code; no pickle/eval/exec introduced. Rule #8 compliant.

**Devil's Advocate.**
What if the user is wrong that the playtest reproduction is the right test? The keystone test (`test_narration_apply_with_real_character_and_em_dash_location`) puts the player at `"The Kestrel — Cockpit"`, calls narration_apply with `location="The Kestrel — Galley"`, and asserts bond grew. But what if production never sends `location="The Kestrel — Galley"` — what if there's an upstream sanitizer that the test bypasses? I checked: `narration_apply.py:984-997` calls `validate_region_name(result.location)` and rejects with `region_entry_rejected_span`. Does that filter run BEFORE `process_room_entry`? Reading the order at narration_apply.py:941-957: location is set on `snapshot.location`, then `process_room_entry` is called. The validation at line 984 happens AFTER `process_room_entry` and only filters whether to add to `discovered_regions` — it does NOT block the rig hook. Confirmed: the wiring works end-to-end as the test claims. What about MP — does the second player's `chargen.complete` re-fire `process_session_open` with their character_id, and would that re-fire the_tea_brew for the new character? The bond_ledger only has one seed entry (rebound to player 1 by then), so `bond_for(player_2_name)` returns None, fires `room.entry_skipped` reason=`no_bond_for_actor`, and exits cleanly. That's the right behavior — multi-PC bond seeds are deferred per the rebind docstring. Confirmed: MP is safe. What about a save reload — does `init_chassis_registry` fire again on rehydration, re-seeding the placeholder, then `rebind` rewrites it with the loaded character's name? Looking at `init_chassis_registry`'s docstring: "Slice scope: fresh-session only. Returning-player save rehydration is deferred to a follow-on." So saved games don't re-run this path — the rebound state persists in the save. That's correct. **Devil's advocate did not find new issues.** The findings above stand.

**Handoff:** Back to Dev (Inigo Montoya) for green rework. Three blocking fixes: (1) reconcile `fired_count` vs `eligible_count` semantics with the docstring/test contract, (2) update `process_room_entry` docstring opening, (3) add `snapshot: GameSnapshot` annotation. The non-blocking observations can be addressed in the same pass at Dev's discretion.

---

## Tea Assessment (verify round 2)

**Verify Round 2 Complete:** Yes
**Simplify pass:** 3 subagents — reuse and efficiency clean; quality returned 3 findings (1 MEDIUM, 2 LOW). 1 applied; 2 deferred.

**Applied:**
- `process_room_entry` docstring opening summary updated. Was "dispatch any rig-coupled auto-fire confrontations eligible at the entered room" — now "match the entered room AND pass the cooldown gate." The body of the docstring already explained the eligible/fired distinction post-rework; only the opening summary was drifted.

**Deferred (LOW, stylistic):**
- Inline cooldown-gate comment could explain *why* the gate is here vs inside `find_eligible_room_autofire`. The rest of the docstring covers this; not worth additional inline noise.
- `emit_room_entry_evaluated` docstring phrasing could be slightly clearer on "no-match (both 0) vs cooldown-blocked (eligible≥1, fired=0)." Current docstring says `fired_count < eligible_count when cooldown blocks dispatch` which is technically correct.

**Reuse + Efficiency:** Clean, no findings. The dropped `cooldown_view` dict construction was a valid cleanup (premature optimization for the typical 1-eligible case). The TYPE_CHECKING import is the standard forward-reference pattern.

**Tests:** 30/30 still green. Lint clean. Verify-round-2 commit `ea4374e` pushed.

**Handoff:** To Reviewer (Westley) for review round 2.

---

## Tea Assessment (verify)

**Verify Phase Complete:** Yes
**Simplify pass:** 3 subagents (reuse, quality, efficiency) returned 9 findings total. 2 high/medium confidence findings applied; 7 deferred as either forward-defensive or premature.

**Applied:**
1. **chassis.py:259** — stale comment updated. Was "(deferred to a follow-on chargen wiring task)"; now points at `rebind_chassis_bonds_to_character` which is the follow-up that landed.
2. **telemetry/spans/rig.py emit_room_entry_skipped docstring** — trimmed to the three reasons actually emitted (`chassis_not_found`, `not_chassis_room`, `no_bond_for_actor`). Notes 47-7 will add `no_magic_state` when magic_state becomes load-bearing.

**Deferred (with rationale):**
- `emit_room_entry_evaluated.fired_count == eligible_count` today — kept as separate field; forward-defensive for the 47-7 contract change where the evaluator may return matched-but-cooldown-blocked entries.
- `process_session_open` thin wrapper — kept; the function name documents intent (evaluate room-entry on session open) that an inline if-guard would erase.
- Refactor `init_chassis_registry` to take character_id — conflates two concerns; world-load and chargen are separate phases that share state but not knowledge.
- Extract `_emit_flat_span` factory across rig.py emitters — 4 instances is premature; ship the factory at instance 6+.
- Inline `rsplit` normalization helper in `process_room_entry` — no recurrence yet.
- `rebind` O(n*m) — accurate description but the loop is honest at current scale (1 chassis × 1 entry); over-engineering claim is misplaced.

**Tests:** 30/30 still green after verify edits. Lint clean. Verify commit `f192218` pushed to origin.

**Handoff:** To Reviewer (Westley/Dread Pirate Roberts) for review phase.

---

## Architect Assessment (spec-reconcile)

**Deviation manifest finalized.** All in-flight deviation logs from TEA, Dev, and Reviewer-audit reviewed for accuracy and 6-field completeness.

**Existing entries verified:**
- TEA (red phase): "No deviations from spec." — accurate; the 47-6 red phase pinned the playtest's runtime input shapes without departing from the AC contract.
- TEA (red rework): "No deviations from spec." — accurate; the strengthening was a single assertion addition that closed the cooldown contract loophole identified by Reviewer; no spec departure.
- Dev (green rework): `find_eligible_room_autofire` signature simplification — 6 fields verified accurate. Spec source quote correct, implementation description matches code, rationale sound, forward impact correctly assessed as "none — no other callers."
- Dev (implementation): `no_magic_state` skip reason deferred — 6 fields verified accurate. Spec source path is "session file AC4" which exists at lines 74-78; spec text quoted correctly; implementation describes 3 reasons shipped vs 4 specced; rationale aligns with CLAUDE.md "Don't add error handling for scenarios that can't happen"; forward impact (47-7 wires it in ~5 lines) is realistic.
- Dev (implementation): `room_not_in_chassis` renamed and split — 6 fields verified accurate. The two-reason taxonomy (`chassis_not_found` for colon-prefix-unknown, `not_chassis_room` for bare/qualified-no-match) is finer-grained than spec; rationale correctly cites Sebastien's GM panel.
- Reviewer (audit): five stamps accepted on existing deviations; one (the `fired_count vs eligible_count` semantics) was flagged as undocumented and routed back through the loop where Dev's green rework (`ced2440`) and TEA's red rework (`e114f27`) resolved it. Stamp ✓ ACCEPTED added by Reviewer round 2 after the resolution.

**Missed deviations added under `### Architect (reconcile)`:**
- Span name format (`room_entry.skipped` → `room.entry_skipped`) — Reviewer-audit had a one-line stamp but it wasn't in the 6-field format. Now logged self-contained per `deviation-format.md`.
- Span attribute concept (`eligible_evaluated` → `evaluated`) — same span-naming family; the spec's compound name was simplified.

**AC accountability:** No ACs were deferred or descoped. All 6 ACs delivered:
- AC1 (em-dash matcher) — DONE via `process_room_entry` matcher fix at `room_movement.py:96-104`.
- AC2 (opening hook integration) — DONE via `process_session_open` wired into chargen-complete at `websocket_session_handler.py:1317-1321`.
- AC3 (bond rebinding) — DONE via `rebind_chassis_bonds_to_character` at `chassis.py:194-212`, wired at `websocket_session_handler.py:1312`.
- AC4 (OTEL spans) — DONE for `chassis_not_found`, `not_chassis_room`, `no_bond_for_actor`, plus `room.entry_evaluated` with chassis_id/room_local_id/eligible_count/fired_count. The fourth reason (`no_magic_state`) is the documented sub-AC deferral to 47-7; constant exported.
- AC5 (regression test with literal em-dash) — DONE via `test_process_room_entry_resolves_em_dash_chassis_qualified_form` and the keystone `test_narration_apply_with_real_character_and_em_dash_location`.
- AC6 (wiring test through narration_apply) — DONE via the keystone test that goes through `_apply_narration_result_to_snapshot`.

**Round-trips:** 1 (red→green→spec-check→verify→review→**REJECTED**→red→green→spec-check→verify→review→APPROVED). The rejection caught a real Sebastien-mode regression (vacuous cooldown test) that the spec-check missed; rework added 11 lines of test, 58 lines of production code, and removed 40 lines of cooldown plumbing.

**Boss audit summary:** Story 47-6 closes the 2026-05-03-coyote_star-3 playtest's silent tea-ritual failure. The fix is layered (matcher + bond rebind + opening hook + OTEL on every silent-return path) and the cooldown semantics now genuinely deliver the GM-panel observability promised by the docstring. Three minor sub-AC deferrals are documented and forward-impacted; the `no_magic_state` reason is the only one that any future story needs to wire up (47-7, ~5 lines). No critical or behavior-breaking deviations.

---

## Architect Assessment (spec-check round 2)

**Spec Alignment:** Aligned. All three Reviewer blockers addressed without over-correction.
**Mismatches Found:** 0 substantive (one trivial deviation already logged)

Verified each blocker:

1. **`fired_count` vs `eligible_count` semantics** — ✓ Cooldown filtering moved out of `find_eligible_room_autofire` into `process_room_entry`. The dispatch loop in room_movement.py:147-172 now per-confrontation gates on cooldown, increments `fired_count` only on actual dispatch, and stamps the cooldown ledger only on fire. `eligible_count = len(eligible)` reflects matched-by-room-and-bond entries; `fired_count` reflects post-cooldown dispatches. The strengthened cooldown test passes — Sebastien's lie detector can now distinguish "no match" from "matched but on cooldown."

2. **Stale `process_room_entry` docstring** — ✓ Lines 60-78 rewrite the opening to describe all three accepted `room_id` formats explicitly. The contract description matches the inline comment block at lines 90-97.

3. **Missing `snapshot: GameSnapshot` annotation** — ✓ chassis.py:194-196. TYPE_CHECKING import at line 16-19 avoids the session↔chassis import cycle while still providing the annotation for static analysis.

**Bonus deviation accepted** (Dev's green-rework deviation log):
- `find_eligible_room_autofire` signature dropped 3 unused parameters (`chassis_id`, `current_turn`, `cooldown_ledger`). Single caller, no test fixtures touched, cleaner post-rework contract. Trivial severity; recommendation A — accept.

**Decision:** Proceed to verify. The rework is precisely what Reviewer asked for; no scope drift, no premature optimization. The keystone test (`test_narration_apply_with_real_character_and_em_dash_location`) still passes — the playtest scenario is closed end-to-end. The cooldown contract test (`test_evaluated_span_emitted_with_fired_zero_when_cooldown_blocks`) now genuinely pins the GM-panel observability contract.

---

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned with three minor cosmetic/taxonomic mismatches and one forward-impact note. No blockers.
**Mismatches Found:** 4

1. **Span name format** (Cosmetic — Trivial)
   - Spec: `room_entry.skipped`, `room_entry.eligible_evaluated`
   - Code: `room.entry_skipped`, `room.entry_evaluated`
   - Recommendation: **A — Update spec.** Dot placement matches project convention (`rig.bond_event`, `rig.voice_register_change`, `rig.confrontation_outcome`). Code is right; spec text was loose.

2. **`no_magic_state` skip reason deferred** (Behavioral — Minor)
   - Spec: AC4 lists 4 reasons including `no_magic_state`.
   - Code: 3 reasons shipped (`chassis_not_found`, `not_chassis_room`, `no_bond_for_actor`); `no_magic_state` deferred per Dev deviation log.
   - Recommendation: **D — Defer.** Dev's rationale is sound: on this branch base `process_room_entry` reads `snapshot.world_confrontations` not `magic_state`, so the defensive check is premature. The `SPAN_ROOM_ENTRY_SKIPPED` constant is exported and emitter helper accepts arbitrary `reason` strings, so 47-7 (magic bars init) wires it in ~5 lines. Already logged as deviation; no further action.

3. **Reason `room_not_in_chassis` renamed and split** (Cosmetic — Trivial)
   - Spec: AC4 listed `room_not_in_chassis` as a single reason.
   - Code: split into `chassis_not_found` (colon-prefix names an unknown chassis_id) and `not_chassis_room` (bare/qualified room name doesn't match any chassis).
   - Recommendation: **A — Update spec.** The two-reason taxonomy is strictly finer-grained — Sebastien's GM panel can tell "you named a chassis I don't know" from "you named a room no chassis owns." Dev's split is the right call.

4. **Em-dash prefix is not validated against chassis name** (Behavioral — Minor, forward impact)
   - Spec: AC1 implicitly assumes the chassis-qualified form `"<Chassis Name> — <Room>"` disambiguates by chassis name.
   - Code: `room_segment = room_id.rsplit(" — ", 1)[-1]` strips *any* prefix that ends in " — ", then matches the trailing room piece against any chassis's `interior_rooms`. The chassis name itself is not verified — `"Some Other Station — Galley"` would still resolve to Kestrel's galley if Kestrel has a `galley` room.
   - Recommendation: **D — Defer.** With one chassis per session (the only shape Coyote Star ships) this is harmless: the only registered chassis is Kestrel, so any " — Galley" string maps to Kestrel's galley — which is correct in a 1-chassis world. The latent ambiguity surfaces only in multi-chassis worlds (player on a freighter docked at a station, both with galleys). File as a forward note for the multi-chassis story; do NOT delay 47-6 over a hypothetical 47-N. Cliffs-of-insanity ascent: solve the cliff in front of you, not the cliff above it.

**Wiring order note (no AC, observation only):** In `websocket_session_handler.py:1305-1320`, `process_session_open` runs immediately after `init_chassis_registry` and `rebind_chassis_bonds_to_character`, but BEFORE `init_magic_state_for_session` (line ~1326+). Currently safe because `process_room_entry` reads `world_confrontations` not `magic_state`. When 47-7 lands and `magic_state` becomes load-bearing for confrontation outputs, this story's wiring order may need to flip. Architect (reconcile) phase will revisit.

**Decision:** Proceed to TEA verify. No hand-back to Dev required. The deviations are properly logged, the mismatches are improvements or properly-deferred future work, and the keystone playtest reproduction test (`test_narration_apply_with_real_character_and_em_dash_location`) passes — the bug the user actually saw is closed.

---

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 32/32 passing in targeted run (16 new 47-6 + 14 existing 47-4 + 2 wiring). Full suite: 28 pre-existing failures unchanged (verified by stash/pop comparison — same failure set with my changes removed).
**Branch:** `feat/47-6-tea-ritual-three-layer-fix` in sidequest-server, pushed to origin (commit `8076dc4`).

**Files Changed:**
- `sidequest-server/sidequest/game/room_movement.py` — em-dash matcher, OTEL on every return path, new `process_session_open` function
- `sidequest-server/sidequest/game/chassis.py` — new `rebind_chassis_bonds_to_character` (idempotent placeholder→real-id rewrite)
- `sidequest-server/sidequest/telemetry/spans/rig.py` — `SPAN_ROOM_ENTRY_SKIPPED`, `SPAN_ROOM_ENTRY_EVALUATED`, two emitter helpers
- `sidequest-server/sidequest/server/websocket_session_handler.py` — wires both new functions into chargen-complete handler
- `sidequest-server/tests/integration/test_tea_brew_runtime_input_shapes.py`, `test_room_entry_otel_spans.py`, `test_opening_galley_autofire.py` — fixture cleanup (no `magic_state` setup needed on this branch base)

**Three-layer fix verified:**
1. Em-dash matcher: `"The Kestrel — Galley"` now resolves to `kestrel:galley` via `rsplit(" — ", 1)[-1]` then chassis.interior_rooms lookup. Colon-prefixed and bare forms unaffected.
2. Bond rebind: `rebind_chassis_bonds_to_character(snap, "Zanzibar Jones")` rewrites placeholder seeds idempotently. Existing real-id entries are never clobbered.
3. Opening hook: `process_session_open` runs eligibility against `snap.location` at chargen-complete time. The keystone test (`test_narration_apply_with_real_character_and_em_dash_location`) reproduces the playtest scenario end-to-end and passes.

**OTEL coverage:**
Every return path in `process_room_entry` now emits a span:
- `room.entry_skipped` reason=`chassis_not_found` (colon-prefix unknown chassis)
- `room.entry_skipped` reason=`not_chassis_room` (room name doesn't match any chassis)
- `room.entry_skipped` reason=`no_bond_for_actor` (chassis matches but actor not in ledger)
- `room.entry_evaluated` (chassis_id, room_local_id, eligible_count, fired_count)

**Production wiring:** `websocket_session_handler.py:1303-1316` — after `init_chassis_registry`, calls `rebind_chassis_bonds_to_character(sd.snapshot, character.core.name)` then `process_session_open(...)`. The chargen-complete path is the single source of session start, so this single wiring covers solo and MP (each player's chargen.complete fires their own rebind + open evaluation).

**Handoff:** To verify phase (TEA simplify-quality pass) per workflow YAML.

---

## Tea Assessment

**RED Phase Complete:** Yes
**Tests Authored:** 17 new tests across 3 files in `sidequest-server/tests/integration/`:
- `test_tea_brew_runtime_input_shapes.py` (8 tests) — AC1, AC3, AC5, AC6
- `test_room_entry_otel_spans.py` (6 tests) — AC4
- `test_opening_galley_autofire.py` (3 tests) — AC2

**RED Verification:** 17/17 new tests fail. Existing 47-4 tests (14) still pass — no regression in synthetic-input shapes.

**Failure modes pinned:**
1. Em-dash matcher: `process_room_entry` doesn't resolve `"The Kestrel — Galley"` → bond/lineage stay zero, cooldown ledger empty
2. Missing rebind: `from sidequest.game.chassis import rebind_chassis_bonds_to_character` is ImportError
3. Missing OTEL constants: `SPAN_ROOM_ENTRY_SKIPPED` and `SPAN_ROOM_ENTRY_EVALUATED` not exported from `telemetry.spans.rig`
4. Missing session-open hook: `from sidequest.game.room_movement import process_session_open` is ImportError

**Dev seams pinned by import (Dev may rename, but the contract is the side effect):**
- `sidequest.game.chassis.rebind_chassis_bonds_to_character(snapshot, character_id) -> None` — idempotent, replaces `"player_character"` placeholder; never overwrites an already-rebound real id
- `sidequest.game.room_movement.process_session_open(snapshot, *, character_id, current_turn) -> None` — runs room-entry eligibility against `snapshot.location` at session-start time
- `sidequest.telemetry.spans.rig.SPAN_ROOM_ENTRY_SKIPPED = "room.entry_skipped"` (with `reason` attribute: `not_chassis_room | no_bond_for_actor | no_magic_state | chassis_not_found`)
- `sidequest.telemetry.spans.rig.SPAN_ROOM_ENTRY_EVALUATED = "room.entry_evaluated"` (with `chassis_id`, `room_local_id`, `eligible_count`, `fired_count`)

**Keystone test:** `test_narration_apply_with_real_character_and_em_dash_location` — full playtest reproduction. If this passes, the 2026-05-03-coyote_star-3 bug is closed end-to-end.

**Branch:** `feat/47-6-tea-ritual-three-layer-fix` (created in sidequest-server subrepo off origin/main, RED commit 43ed70a)

**Rule Coverage (python.md checklist):**
- #6 Test quality: every test asserts a specific value (`>`, `==`, set membership), not vacuous truthy. All have failure messages.
- #3 Type annotations: helpers are private (`_bootstrap_*`, `_span_attrs_by_name`); fixtures use existing typed contracts.
- #4 Logging: tests assert on OTEL span emission, the project's structured-log lever (CLAUDE.md OTEL principle).
- #1 Silent exceptions: tests pin that silent returns get spans — they enforce the rule directly.

**Handoff:** To Dev (Inigo Montoya) for green phase. The four bugs are interdependent — fixing matcher alone won't pass the rebind tests, fixing rebind alone won't pass the matcher tests. Recommend implementing in order: rebind → matcher → OTEL spans → session-open hook. Each layer is small (≤30 lines).

---

## Sm Assessment

**Setup Complete:** Yes
**Source:** Bugs surfaced from solo playtest audit of save `2026-05-03-coyote_star-3` (Zanzibar Jones, 22 turns). User identified the missed tea ritual at the end; deeper audit revealed three layered failure modes plus a cross-cutting OTEL gap.

**Why this story matters:**
This is a Sebastien-mode story — the existence of `the_tea_brew` as a defined confrontation that *never fired* across multiple eligible moments is exactly the failure mode CLAUDE.md warns about: "Claude is excellent at 'winging it' — writing convincing narration with zero mechanical backing." The narrator wrote a beautiful tea ritual at turn 22; the engine recorded zero state change. The fix isn't just one bug — three independent gates all need correcting before the ritual can fire, and every silent return must emit OTEL so this class of regression can never hide again.

**Bond rebind is load-bearing:** Even if TEA writes a perfect test for the room-name matcher, the test will fail because `chassis.bond_for(actor)` returns None for the placeholder seed. The three layers must be tested *and* implemented as one unit — that's why this is a single 5pt story instead of three 2pt stories.

**Predecessor:** Story 47-4 marked done shipped this confrontation but with all three latent bugs. This story closes 47-4's silent-failure modes.

**Files Reviewed for Setup:** Audit-derived only — SM did not read implementation files. TEA and Dev will read the code.

**Branch:** `feat/47-6-tea-ritual-three-layer-fix` (from main)
**Workflow:** tdd (red → green → review → finish)
**Repos:** server only
**Handoff:** To TEA (Fezzik) for red phase — write 6 failing tests, one per AC. AC5 (literal em-dash regression) is the keystone test.

---

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (red phase)
- No upstream findings during red phase. Existing 47-4 tests use synthetic colon-prefixed room ids (`"kestrel:galley"`) and the `"player_character"` placeholder character — they pin the happy-path contract but did not exercise the runtime input shapes that broke in playtest. The new 47-6 tests close that gap; the original tests stay valid.

### TEA (red rework)
- No upstream findings during red rework. Strengthened cooldown test in response to Reviewer's HIGH finding (cross-confirmed by 3 subagents). Strengthening is local: one new assertion on the same span pulled by the existing test. Dev's green-rework will need to change `find_eligible_room_autofire`'s cooldown contract — that's the only meaningful upstream impact, and it's contained inside the rig auto-fire subsystem.

### Reviewer (code review round 2)
- No upstream findings. All round-1 blockers resolved by Dev's rework (commits `ced2440`, `ea4374e`) plus TEA's red rework (commit `e114f27`). Subagent fan-out (preflight, comment-analyzer, test-analyzer, rule-checker) all returned clean — 0 findings, 0 dismissals, 0 deferrals.

### Reviewer (code review round 1)
- **Gap** (blocking, RESOLVED): `emit_room_entry_evaluated` cannot deliver the diagnostic capability its docstring promises. Cross-confirmed by 3 subagents. Affects `sidequest-server/sidequest/game/room_movement.py:162` and `sidequest-server/sidequest/telemetry/spans/rig.py:121-126` (decide whether to fix the semantics or trim the docstring + rename field). *Found by Reviewer during code review.*
- **Gap** (blocking): `process_room_entry` docstring opening contradicts the three-format resolver. Affects `sidequest-server/sidequest/game/room_movement.py:60-66` (rewrite opening sentence). *Found by Reviewer during code review.*
- **Gap** (blocking): `rebind_chassis_bonds_to_character` snapshot parameter untyped at public boundary. Affects `sidequest-server/sidequest/game/chassis.py:193` (add `snapshot: GameSnapshot`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Missing negative test for em-dash sensitivity (ASCII hyphen variant). Affects `sidequest-server/tests/integration/test_tea_brew_runtime_input_shapes.py` (add a test that feeds `"The Kestrel - Galley"` and asserts the_tea_brew does NOT fire). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `chassis.py` has no `__all__`. Pre-existing absence; new public symbol added. Affects `sidequest-server/sidequest/game/chassis.py` (add `__all__` listing the public surface). *Found by Reviewer during code review.*

### Dev (green rework)
- **Improvement** (non-blocking): Em-dash sensitivity negative test (Reviewer flagged) deferred to a follow-up. Affects `sidequest-server/tests/integration/test_tea_brew_runtime_input_shapes.py` (add a test that feeds `"The Kestrel - Galley"` with ASCII hyphen and asserts the_tea_brew does NOT fire — pins the matcher's exact-separator contract). *Found by Reviewer; deferred by Dev to keep rework focused.*
- **Improvement** (non-blocking): `find_eligible_room_autofire` signature simplification — three parameters dropped because no test or production caller used them after the cooldown move. Net cleaner contract. *Found by Dev during rework.*

### Dev (implementation)
- **Gap** (non-blocking): Pre-existing test failures on the branch base (origin/main of sidequest-server) — 28 failures across `tests/server/test_mp_auto_seat_on_connect.py`, `test_opening_turn_bootstrap.py`, `test_session_handler_localdm_offline.py`, `test_turn_manager_round_invariant.py`, `test_multiplayer_party_status.py`. Stash/pop comparison confirms these existed before 47-6 changes. Affects no 47-6 paths but should be filed as a blocker for future stories that touch the multiplayer/opening-bootstrap code (the failing assertion is `unexpected keyword argument 'room'` — a signature mismatch from a recent refactor). *Found by Dev during implementation.*
- **Question** (non-blocking): The `make_minimal_coyote_star_magic_state` test helper exists on `feat/adr-094-orrery-callouts` (commit 85d51f0, story 45-43 snapshot split-brain Wave 1) but not on origin/main. When 45-43 merges, story 47-7 (magic bars init) should add the helper to `tests/integration/conftest.py` and re-introduce the `no_magic_state` skip path with a corresponding test. The constant `SPAN_ROOM_ENTRY_SKIPPED` is already exported, so the wiring will be small. Affects `sidequest-server/tests/integration/conftest.py` and `sidequest/game/room_movement.py:process_room_entry`. *Found by Dev during implementation.*

---

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (red phase)
- No deviations from spec.

### TEA (red rework)
- No deviations from spec.

### Reviewer (audit)
- **`emit_room_entry_evaluated` fired_count vs eligible_count semantics:** UNDOCUMENTED deviation. Architect spec-check accepted "fired_count==eligible_count today" as forward-defensive. Three reviewer subagents (comment-analyzer, test-analyzer, rule-checker) flagged that the docstring promises a distinction (`fired_count < eligible_count when cooldown blocks`) the implementation cannot deliver, and the cooldown-blocking test passes vacuously. Severity: H. The story's stated purpose is GM observability — this deviation defeats that purpose. Rejecting back to Dev. → **RESOLVED in green rework** (commit `ced2440`): cooldown filtering moved out of `find_eligible_room_autofire` into `process_room_entry` dispatch loop; strengthened test (`e114f27`) now passes legitimately. ✓ ACCEPTED by Reviewer round 2.
- **`find_eligible_room_autofire` signature simplification:** ✓ ACCEPTED by Reviewer — Dev's deviation log is sound; single caller, no test fixtures broken, post-rework cleanup.
- **Span name format deviation** (`room_entry.skipped` → `room.entry_skipped`): ✓ ACCEPTED by Reviewer — code follows project convention (`rig.bond_event`, `rig.confrontation_outcome`); spec text was the loose one.
- **`no_magic_state` skip reason deferred to 47-7:** ✓ ACCEPTED by Reviewer — Dev's rationale is sound; magic_state isn't load-bearing on this branch base. Constant exported, ready for 47-7 wiring.
- **`room_not_in_chassis` renamed and split** (into `chassis_not_found` + `not_chassis_room`): ✓ ACCEPTED by Reviewer — finer-grained taxonomy serves Sebastien's lie detector better.
- **Em-dash prefix not validated against chassis name:** ✓ ACCEPTED by Reviewer — single-chassis world is the only current shape; defer to multi-chassis story per Architect's note.

### Dev (green rework)
- **`find_eligible_room_autofire` signature simplification**
  - Spec source: Reviewer Assessment (this session, "Reviewer Assessment" section, [HIGH] [DOC][TEST][RULE] row).
  - Spec text: "Either: (a) move cooldown filtering OUT of `find_eligible_room_autofire` and INTO `process_room_entry`, so `eligible` includes matched-but-cooldown-blocked entries and `fired` excludes them..."
  - Implementation: Did move cooldown filtering, AND additionally dropped three parameters that became unused (`chassis_id`, `current_turn`, `cooldown_ledger`). The function now takes only `confrontations`, `room_local_id`, `bond_tier_chassis`.
  - Rationale: Single caller; the orphaned parameters added clutter without serving any consumer. Removing them is the cleaner finish to the contract change Reviewer asked for.
  - Severity: trivial
  - Forward impact: none — no other callers; if a future caller wanted cooldown-aware filtering they should compose `process_room_entry`'s pattern (call this function, then per-entry cooldown check) rather than re-bundle the gate.

### Architect (reconcile)
- **Span name format: `room_entry.skipped` → `room.entry_skipped` (and `room_entry.eligible_evaluated` → `room.entry_evaluated`)**
  - Spec source: session file `## Acceptance Criteria` AC4 (lines 75-77 in this session file).
  - Spec text: "`room_entry.skipped` (with reason: `not_chassis_room`, `no_bond_for_actor`, `no_magic_state`, `room_not_in_chassis`)" and "`room_entry.eligible_evaluated` (with chassis_id, room_local_id, eligible_count, fired_count)"
  - Implementation: shipped as `room.entry_skipped` and `room.entry_evaluated` (constants in `sidequest/telemetry/spans/rig.py:23-24`).
  - Rationale: project span-name convention is `<domain>.<event>` (e.g., `rig.bond_event`, `rig.confrontation_outcome`, `rig.voice_register_change` per `rig.py:20-22`). The spec's underscore-separated names broke that convention; Dev followed the convention and the Reviewer-audit stamp accepted it. Architect spec-check round 1 also accepted under recommendation A.
  - Severity: trivial
  - Forward impact: none — no consumer queries by the spec's underscore-form name yet (spans are flat-only; no SPAN_ROUTES entry; the GM dashboard reads the actual emitted name). Future ADR or schema docs that reference these span names should use the dot-form constants.

- **Span attribute key for evaluator output: `eligible_evaluated` → `evaluated`**
  - Spec source: session file AC4 (line 76).
  - Spec text: AC4 names the span as `room_entry.eligible_evaluated` — the attribute concept is "eligibility was evaluated."
  - Implementation: shipped as `room.entry_evaluated` (one word: "evaluated"); the spec's compound `eligible_evaluated` was simplified.
  - Rationale: drops a redundant adjective. The span emits `eligible_count` and `fired_count` already; the noun "eligibility" is implicit in the field set. Trivially shorter, no semantic change.
  - Severity: trivial
  - Forward impact: none.

### Dev (implementation)
- **`no_magic_state` skip reason deferred**
  - Spec source: session file AC4 — "every return path emits a watcher span: `room_entry.skipped` (with reason: `not_chassis_room`, `no_bond_for_actor`, `no_magic_state`, `room_not_in_chassis`)"
  - Spec text: lists `no_magic_state` as one of four required reasons.
  - Implementation: shipped three reasons (`not_chassis_room`, `no_bond_for_actor`, `chassis_not_found`); omitted `no_magic_state`.
  - Rationale: On this branch base (origin/main of sidequest-server, pre-45-43), `process_room_entry` reads from `snapshot.world_confrontations` not `snapshot.magic_state`. Setting `magic_state = None` does not affect the function's behavior; a defensive check would be premature error handling for a scenario that can't currently happen. Per CLAUDE.md "Don't add error handling for scenarios that can't happen." The constant `SPAN_ROOM_ENTRY_SKIPPED` is exported and ready for 47-7 to wire when magic_state becomes load-bearing.
  - Severity: minor
  - Forward impact: minor — story 47-7 (magic bars init) will need to add the `no_magic_state` skip path and one test. The constant already exists; the wiring is ~5 lines.
- **`room_not_in_chassis` reason renamed to `chassis_not_found`**
  - Spec source: session file AC4 reason list.
  - Spec text: lists `room_not_in_chassis` as a reason.
  - Implementation: used `chassis_not_found` for the colon-prefixed-but-unknown-chassis path; `not_chassis_room` for the bare-name-doesn't-match-any-chassis path.
  - Rationale: The two distinct paths needed distinct names. `not_chassis_room` matches "the room you named isn't aboard any chassis," while `chassis_not_found` matches "you named a chassis prefix that isn't registered." Combining them under `room_not_in_chassis` would erase that distinction. Sebastien's GM panel benefits from the finer-grained reason.
  - Severity: minor
  - Forward impact: none — Reviewer should confirm the two-reason taxonomy is preferable; if not, can rename in a follow-up.

---

## TDD Workflow Notes

**Red Phase (TEA):**
- Write failing tests for all four bugs before touching implementation
- Test 1: Narrator string format matcher (em-dash input)
- Test 2: Bond ledger rebinding at session-start
- Test 3: Opening pipeline calls process_room_entry (or equivalent)
- Test 4: OTEL spans emitted on all return paths
- Test 5: Regression test with literal `"The Kestrel — Galley"` string
- Test 6: Integration test through full narration_apply flow
- **Do NOT write implementation code yet.** Let the tests fail.

**Green Phase (DEV):**
- Implement fixes in order of dependency: rebinding → matcher → opening hook → OTEL
- Make tests pass
- Verify OTEL spans appear on GM dashboard

**Review Phase (REVIEWER):**
- Verify all 6 tests pass
- Verify narrator integration: cold-start and narrator-driven updates both fire
- Verify GM panel shows room_entry spans with correct reason codes
- Check for regressions in other auto-fire confrontations

**Finish:**
- Update sprint tracker
- Archive this session file to sprint/archive/47-6-session.md

---

## Notes for DEV & REVIEWER

- **No silent fallbacks:** If the matcher rejects a string, emit a span saying why. Never silently try alternative formats.
- **OTEL is load-bearing:** The GM dashboard is the lie detector. If a subsystem isn't emitting spans, we can't verify the fix works.
- **Integration matters:** Unit tests of process_room_entry in isolation don't count. Must prove the full pipeline from narrator→dispatch→narration_apply→process_room_entry→watcher works.
- **Character ID mismatch is critical:** The bond_ledger entry with placeholder `character_id` will break any bond lookup. Session-start rebinding must happen before any gameplay logic touches bonds.