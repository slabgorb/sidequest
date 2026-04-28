---
story_id: "45-15"
epic: "45"
workflow: "trivial"
---
# Story 45-15: Consumed-state items removed from inventory

## Story Details
- **ID:** 45-15
- **Epic:** 45 — Playtest 3 Closeout
- **Workflow:** trivial
- **Type:** bug
- **Priority:** p2
- **Points:** 1
- **Repos:** server

## Description

Playtest 3 Felix: maintenance_kit.state=Consumed after patch-foam use (rounds 14-16) and foil-strip tear (round 48), but kit remained in inventory list with quantity=1. Extractor writes Consumed but removal pass never runs. Either drop items with state=Consumed at end-of-turn, OR don't set Consumed without also removing.

**Source:** 37-39 sub-5

## Acceptance Criteria
- [ ] Items with state=Consumed are removed from inventory at end-of-turn
- [ ] Consumed state transition path fires with same intent as items_lost
- [ ] OTEL span emitted on item consumption/removal (item_id, old_state, action)
- [ ] Playtest 3 save verification: consumed items no longer appear in inventory
- [ ] No production call sites missed (grep clean on Consumed state)

## Workflow Tracking
**Workflow:** trivial
**Phase:** implement
**Phase Started:** 2026-04-28T01:14:45Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28T01:14:45Z | 2026-04-28T01:30:00Z | ~15m |
| implement | 2026-04-28T01:30:00Z | - | - |

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/agents/narrator.py` — add `items_consumed` to valid game_patch fields + CRITICAL INVENTORY RULE updated to require items_consumed for one-shot consumables
- `sidequest-server/sidequest/agents/orchestrator.py` — `NarrationTurnResult.items_consumed` field, extraction count log, returned in `extract_structured_from_response`, threaded into `NarrationTurnResult` construction
- `sidequest-server/sidequest/server/narration_apply.py` — `items_consumed` lane removes first matching name (case-insensitive); unmatched consumes surface via `unmatched_consumes_count` per CLAUDE.md no-silent-fallback
- `sidequest-server/sidequest/telemetry/spans.py` — `inventory_narrator_extracted_span` accepts `consumed=` kwarg, serializes to `consumed_json`/`consumed_count`; `SPAN_ROUTES[SPAN_INVENTORY_NARRATOR_EXTRACTED]` exposes `consumed`/`consumed_count` on routed event
- `sidequest-server/tests/server/test_encounter_apply_narration.py` — 2 new unit tests (consume removes + OTEL span; unmatched consume increments span counter)
- `sidequest-server/tests/integration/test_inventory_wiring.py` — 1 new integration test (end-to-end span → route → watcher hub)

**Tests:** 18/18 passing on touched files (3 new). Pre-existing tests still green (388/388 in agents+watcher_events).
**Lint:** 3 pre-existing ruff errors in `orchestrator.py` (lines 815, 1464, 1682) — none in my edits, confirmed out-of-scope per session instructions.
**Branch:** feat/45-15-consumed-items-removed-from-inventory (pushed)
**PR:** https://github.com/slabgorb/sidequest-server/pull/93 (base: develop)

**Handoff:** To review

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): No production code currently writes `state=Consumed` to any inventory item — grep on `state.*Consumed` came up empty across `sidequest/` and `tests/`. The Playtest 3 Felix bug ("kit remained at quantity=1 after patch-foam use") is plumbing-shaped: there's no consume verb in the narrator extraction pipeline at all, so the kit was never updated. The fix-shape is therefore the *second* AC1 option ("don't set Consumed without removing") — we add a `items_consumed` lane that drops the item outright. *Found by Dev during implementation.*
- **Conflict** (non-blocking): Story 45-14 (`feat/45-14-discarded-weapon-state-transition`) is **not yet merged to develop** — it lives on its branch. 45-15 was therefore branched from develop without 45-14's `items_discarded` plumbing. Both PRs add fields to `NarrationTurnResult`, the narrator prompt, the OTEL span, and the route extractor. Whichever lands second (45-14 or 45-15) will need a small merge to combine the new fields. The shapes are intentionally parallel so the merge should be mechanical. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Lane name:** Story prompt suggested `items_consumed` *or* an end-of-turn sweep. Picked `items_consumed` (lane-based) because it mirrors 45-14's shape exactly (smallest delta, single seam) and avoids needing a separate sweep pass. The lane removes the item outright on consume rather than writing `state=Consumed` and sweeping later — satisfies AC1's "either" branch ("don't set Consumed without removing") and is one fewer state-machine transition.
- **AC interpretation:** Story AC mentions "old_state" on the OTEL span. Since the lane removes outright (no Consumed state ever written), the span carries `consumed_json` (list of consumed names) and `consumed_count` instead — equivalent visibility for the GM panel ("X items spent this turn") without modeling a state we never enter.

## Reviewer Assessment

**Verdict:** APPROVED
**Reviewer:** Westley
**Reviewed at:** 2026-04-27 (PR #93)

### Verification

- **Tests:** 18/18 pass on touched suites (`tests/server/test_encounter_apply_narration.py` + `tests/integration/test_inventory_wiring.py`). Three new tests cover positive remove, OTEL span attributes, unmatched-fallback counter, and end-to-end span→route→hub integration.
- **Wiring traced end-to-end:** narrator prompt names `items_consumed` → `extract_structured_from_response` (orchestrator.py:584) extracts → `NarrationTurnResult.items_consumed` (orchestrator.py:267, populated at orchestrator.py:1617) → `_apply_narration_result_to_snapshot` called from production narrator turn at `session_handler.py:3208` → inventory pop + `inventory_narrator_extracted_span` (narration_apply.py:345) → `WatcherSpanProcessor` → `SPAN_ROUTES[SPAN_INVENTORY_NARRATOR_EXTRACTED]` (spans.py:376) → watcher hub `state_transition`. Reachable from live narrator turn path. No half-wired surface.
- **Pattern observed:** Mirrors 45-14's `items_discarded` lane shape exactly — same 4-file fanout (narrator.py prompt, orchestrator.py result+extract, narration_apply.py mutation, spans.py route+kwarg) and same OTEL signal triple (`*_json` / `*_count` / `unmatched_*_count`). Dev correctly preserved parity rather than refactoring both lanes together (out-of-scope for 1pt).
- **Approach validity:** Dev picked AC1's second branch ("don't set Consumed without removing"). Grep on `state.*Consumed` across `sidequest/` came up empty — no production code reads or writes `state=Consumed`, so the transitional state was never observed. Removal-on-extract is the right call: fewer state-machine transitions, lower surface, and the OTEL signal still distinguishes "spent on use" from "given away" via separate lanes.
- **Error handling:** `unmatched_consumes` logs WARNING and increments span counter — no silent fallback when narrator hallucinates a consume on an item not in inventory. Verified by `test_items_consumed_unmatched_logs_and_emits_count`.
- **Lane disambiguation:** Prompt is unambiguous standalone — "USES UP a consumable… function was spent" with explicit contrast to items_lost ("given-away/stolen/destroyed") and items_gained ("acquisition"). Examples (patch-foam applied, ration eaten, charge expended) match exactly the Felix bug shape. items_lost/items_gained verb lists unchanged so no regression risk on existing lanes.
- **Security/data flow:** narrator-derived names are lowercased before equality match and pop — same case-insensitive pattern as items_lost. No SQL/path/eval surface; pure list mutation under existing snapshot semantics.

### Findings

| Severity | Issue | Location | Notes |
|----------|-------|----------|-------|
| [LOW] | `consumed_names` stores lowercased name (matches items_lost behavior) — GM panel may display "maintenance kit" instead of "Maintenance Kit" | `narration_apply.py:327` | Pre-existing pattern from items_lost. Not introduced by this PR. Worth a follow-up if/when GM panel displays consumed names. Non-blocking. |
| [INFO] | Merge with 45-14 (still on its own branch) is mechanical-but-load-bearing: second-merger must add the missing lane to ALL six touch points (Valid-fields list, CRITICAL INVENTORY RULE tail, extraction log format, extract return dict, NarrationTurnResult ctor, inventory `if` guard, span kwargs, route fields). Both diffs are additive so no semantic conflict, but 6-file fanout means a careless merge could drop a lane. | n/a | Already flagged in Dev Delivery Findings. SM should sequence the merges and have the second one re-run the full inventory-wiring suite. Non-blocking for this PR. |

### Observations

1. Wiring is end-to-end reachable from `session_handler.py:3208` (production narrator turn).
2. OTEL span emits `consumed_json`, `consumed_count`, `unmatched_consumes_count` — full GM-panel lie-detector signal.
3. No `state=Consumed` is written anywhere — AC1 satisfied by construction.
4. Prompt lane verbs are non-overlapping with items_lost/items_gained.
5. Three new tests; one is an integration test that exercises the route → watcher hub seam (CLAUDE.md wiring-test mandate satisfied).
6. `test_items_consumed_unmatched_logs_and_emits_count` confirms no-silent-fallback on hallucinated consumes.
7. Trivial scope honored: 6 files, +270/-26, no adjacent rewrites or speculative refactors.

### Deviation Audit

- **Lane name (`items_consumed` vs end-of-turn sweep):** ACCEPTED. Lane-based mirrors 45-14, single seam, fewer state transitions.
- **AC interpretation (`old_state` field absent):** ACCEPTED. Span carries `consumed_json` + `consumed_count` + `unmatched_consumes_count` — equivalent or better visibility for the GM panel since no state is ever entered.

**Handoff:** To SM for finish-story.
