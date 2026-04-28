---
story_id: "45-14"
epic: "45"
workflow: "trivial"
---
# Story 45-14: Discarded weapon transitions out of state=Carried

## Story Details
- **ID:** 45-14
- **Epic:** 45 — Playtest 3 Closeout
- **Workflow:** trivial
- **Type:** bug
- **Priority:** p2
- **Points:** 1
- **Repos:** server

## Description

Playtest 3 Blutka: 'abandons the spear where it stands — shaft quivering in scavenger meat' (round 9) but spear still showed state=Carried in final inventory. Narrator-extracted discard verbs must move item state to Discarded (or remove from inventory). Wire the discard path through the same narration_apply pipeline as items_lost.

**Source:** 37-39 sub-4

## Acceptance Criteria
- [ ] Narrator-extracted discard verbs move item state to Discarded (or remove from inventory)
- [ ] Discard path wired through narration_apply pipeline same as items_lost
- [ ] OTEL span emitted on item state transition (item_id, old_state, new_state, action)
- [ ] Playtest 3 save verification: discarded items no longer appear as state=Carried in inventory
- [ ] No production call sites missed (grep clean on item state transitions)

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-04-28T01:01:33Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28T01:01:33Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): `just server-check` was already failing with 173 pre-existing ruff errors on `develop` before this story (E402 import ordering, F841 unused vars, SIM108 ternary in `orchestrator.py:812/1461/1679`, etc.). Touched files (`narration_apply.py`, `narrator.py`, `spans.py`, both test files) lint clean; the pre-existing failures sit outside the 1pt scope. Affects whole tree; needs a separate cleanup story or a `just lint-touched` target. *Found by Dev during implementation.*
- **Improvement** (non-blocking): Item `state` is currently a free-form string ("Carried", "Discarded") — there is no `ItemState` enum or formal validator. New states are introduced by string convention and `views.py` filters via string compare (`str(item.get("state", "Carried")) == "Carried"`). A future story should formalize this into an enum to prevent typo drift. Affects `sidequest/server/views.py:317`, `sidequest/server/session_handler.py:2807`, `sidequest/game/commands.py:147`. *Found by Dev during implementation.*
- **Question** (non-blocking): AC4 from the session file ("Playtest 3 save verification: discarded items no longer appear as state=Carried") is not verifiable from a unit test. The fix lands the wiring but only proves itself end-to-end on a fresh playtest run with the updated narrator prompt. Recommend a follow-up playtest scenario or replay test against the Blutka save once the prompt update reaches production. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Chose state transition over removal:** AC1 said "transitions out of Carried (to Discarded, or removed entirely)" — both options were acceptable. Implemented state transition (item kept in inventory with `state="Discarded"`) instead of removal. Reason: discarded items are narratively recoverable ("the spear stands quivering in scavenger meat" — Blutka can return for it), and `views.py` already filters Discarded out of the player-facing carried view, so the UX is identical to removal but preserves continuity. `items_lost` retains its remove-from-inventory semantics for the gone-from-continuity case (given/stolen/destroyed).
- **Added new `items_discarded` field instead of overloading `items_lost`:** Spec said "wire through the same `narration_apply` pipeline as `items_lost`" — the apply seam is shared (single inventory block, single OTEL span), but the JSON patch field is separate. Reason: `items_lost` already carried "drops" semantics in the prompt, and the playtest bug shows the narrator simply wasn't emitting that field for "abandons" — adding `items_discarded` lets the prompt explicitly disambiguate "still in the world (recoverable)" from "gone forever" so the model can't conflate them.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/agents/orchestrator.py` — added `items_discarded` field on `NarrationTurnResult`, plumbed extraction through `extract_structured_from_response` and `Orchestrator` construction, extended extraction-count log line
- `sidequest-server/sidequest/agents/narrator.py` — added `items_discarded` to valid fields list, added items_discarded prompt section, expanded CRITICAL INVENTORY RULE to call out abandon/drop verbs explicitly
- `sidequest-server/sidequest/server/narration_apply.py` — added items_discarded apply block (Carried → Discarded transition, equipped → False), unmatched-discard counter for no-silent-fallback compliance, extended log + span attrs
- `sidequest-server/sidequest/telemetry/spans.py` — extended `inventory_narrator_extracted_span` with `discarded` parameter, extended `SPAN_ROUTES[SPAN_INVENTORY_NARRATOR_EXTRACTED]` to surface `discarded` / `discarded_count` fields
- `sidequest-server/tests/server/test_encounter_apply_narration.py` — added 2 unit tests (state transition + unmatched discard)
- `sidequest-server/tests/integration/test_inventory_wiring.py` — added 1 wiring test (end-to-end span → route → hub)

**Tests:** 2667/2667 passing (was 2666 before; +1 unit test, +1 unit test, +1 integration test means +3 net — all green)
**Branch:** feat/45-14-discarded-weapon-state-transition (pushed)
**PR:** https://github.com/slabgorb/sidequest-server/pull/92 (base: develop)

**Handoff:** To review

## Reviewer Assessment

**Verdict:** APPROVED
**Reviewer:** Westley
**Date:** 2026-04-28

**Tests verified locally:** 18/18 pass on focused suite (`tests/server/test_encounter_apply_narration.py` + `tests/integration/test_inventory_wiring.py`). Full server gate per Dev: 2667/0.

### Adversarial review — confirmed observations

1. **Wiring traced end-to-end (verified, not trusted).** New `items_discarded` lane lives on `NarrationTurnResult` (orchestrator.py:264), is populated from extraction at `orchestrator.py:1614`, returned from the module-level `run_narration_turn` (line 1639), called by `session_handler.py:3164`, and the result is fed to `_apply_narration_result_to_snapshot` at `session_handler.py:3208`. The apply seam at `narration_apply.py:254-335` handles the new lane. Production WS path is reachable. Wiring test (`test_inventory_wiring.py:213-289`) exercises route → hub. Good.

2. **Lane semantics defensible.** AC1 explicitly accepted "transitions out of Carried (to Discarded, OR removed entirely)" — Dev chose the transition variant and documented it in Design Deviations with sound rationale (recoverability + `views.py:317` filters Discarded out of the carried view, so player UX is identical). Splitting into a new lane (rather than overloading `items_lost`) is the right call: prompt can now disambiguate "given away" (gone) vs "abandoned" (recoverable), and the narrator was already failing to emit `items_lost` for "abandons" — a signal the verbs needed separate buckets. Confirmed.

3. **Downstream Carried filters all string-compare to "Carried".** `views.py:317`, `game/commands.py:147`, `session_handler.py:2807` all use `str(item.get("state", "Carried")) == "Carried"`. Flipping to `"Discarded"` correctly drops the item from every carried-view code path. No grep miss. AC5 satisfied.

4. **OTEL pattern parity.** `discarded` / `discarded_count` / `unmatched_discards_count` mirror existing `gained` / `lost` shape. `discarded_json` serialized via the same `_json.dumps(list(...))` pattern as `gained_json`/`lost_json` — avoids the OTEL primitive-types silent-drop trap. Span route at `spans.py:376-385` surfaces `discarded` to the GM dashboard. Lie-detector for "abandons the spear" prose vs inventory state is now in place — exactly the OTEL Observability Principle at work.

5. **No-silent-fallback compliance is real.** Unmatched discards (narrator hallucinates a discard for an item not in inventory) emit a `logger.warning` AND surface a non-zero `unmatched_discards_count` on the span. Test `test_items_discarded_unmatched_logs_and_emits_count` (test_encounter_apply_narration.py:336-358) proves the GM panel sees the gap. Loud failure ✓.

6. **Prompt rule is unambiguous.** New prompt text (narrator.py:99-128) cleanly separates "GONE from continuity" (`items_lost` — given/traded/stolen/destroyed/consumed) from "remains in the world (recoverable)" (`items_discarded` — drops/abandons/leaves/sets down). The prefer-`items_discarded`-when-unsure tiebreaker biases toward the safer (recoverable) default — sensible. CRITICAL INVENTORY RULE was extended (not replaced), preserving the existing items_lost reflex while adding the discard channel. No regression risk to existing items_lost cases.

7. **Match guard is correct.** Discard loop only matches items currently in `state == "Carried"` (narration_apply.py:322). A double-discard or discard-of-already-Discarded item correctly falls through to `unmatched_discards` rather than silently no-op'ing — preserves the lie-detector signal.

8. **Defensive `getattr` on `items_discarded`.** Line 254: `getattr(result, "items_discarded", None) or []`. Slightly belt-and-braces given the field is now declared on `NarrationTurnResult` with a default, but harmless and makes the apply seam tolerant of stub/legacy `result` objects in tests. Acceptable.

### Stringly-typed `state` — non-blocking

Dev flagged this in Delivery Findings: `state` remains a free-form string. The diff doesn't make this worse (it adds one more string literal, `"Discarded"`, alongside the existing `"Carried"`). The downstream filters all default to `"Carried"`, so a typo on the producer side would silently de-carry the item — that's a real footgun, but it predates this story and the 1pt budget shouldn't fix it. Dev's recommendation to formalize an `ItemState` enum in a follow-up is correct. Filed in Delivery Findings, no action needed here.

### Trivial scope — Dev stayed tight

5 source files (orchestrator.py, narrator.py, narration_apply.py, spans.py + 2 test files). One narrow plumbing path. No drive-by refactors. No stubs. No silent fallbacks. The Dev note about pre-existing 173 ruff errors on `develop` is appropriate — out of scope.

### Deviation audit

Both Dev deviations are ACCEPTED:
- **State transition over removal** — explicitly permitted by AC1, plus the recoverability rationale is genre-appropriate (the spear *is* still narratively present in scavenger meat).
- **New `items_discarded` field** — the apply pipeline is shared (single inventory block, single OTEL span), which is what AC2 actually demanded ("wired through the same `narration_apply` pipeline as `items_lost`"). Adding a separate JSON patch field is a *prompt-engineering* change, not a pipeline split.

### Patterns observed

- **Good pattern:** New lane mirrors `items_lost`'s shape exactly — same dict structure, same case-insensitive name match, same `break`-on-first-match semantics. Span route attribute naming follows `<lane>` / `<lane>_json` / `<lane>_count`. Easy to read, easy to extend.
- **Good pattern:** Test docstrings cite the actual playtest evidence ("Playtest 3 Blutka turn 9: 'abandons the spear where it stands — shaft quivering in scavenger meat'") — this is the project's preferred documentation style and makes regressions easy to interpret.

### Findings table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| (none)   | No Critical/High/Medium issues found | — | — |

**Handoff:** To SM for finish-story.

---

**Session file created:** 2026-04-28
**Branch target:** sidequest-server (develop → feat/45-14-discarded-weapon-state-transition)
