---
story_id: "71-15"
jira_key: ""
epic: "71"
workflow: "tdd"
---
# Story 71-15: ADR-055 — wire per-transition trope-tick + item resource depletion on room-graph movement

## Story Details
- **ID:** 71-15
- **Jira Key:** (none — personal project, no Jira)
- **Workflow:** tdd (phased)
- **Stack Parent:** none
- **Points:** 5
- **Priority:** p2
- **Repos:** sidequest-server
- **Branch:** feat/71-15-room-graph-movement-trope-item-tick

## Story Context

**IMPORTANT:** This story has NO explicit acceptance criteria in the sprint YAML. ACs must be derived from:
1. The context document at `sprint/context/context-story-71-15.md` (comprehensive spec)
2. ADR-055 (`docs/adr/055-room-graph-navigation.md`), especially the 2026-05-28 amendment

The context file pins two **confirmed unwired gaps** from ADR-055's 2026-05-02 status:
- Per-transition trope tick: `grep tick_on_room_transition` returns zero hits. Function is nonexistent.
- Item resource depletion: `uses_remaining` is written but never decremented on movement.

### Why This Matters

Room-graph dungeon crawl (beneath_sunden, ADR-106) creates pressure through traversal — Keeper awareness escalates as players go deeper, resources (torch) deplete. With neither mechanic firing, movement is consequence-free. This guts the tension model and makes the dungeon a diorama instead of a living, ablating space (SOUL: "Living World", "Cut the Dull Bits").

### AC Summary (from context-story-71-15.md)

1. Per-transition trope tick (room-graph mode only): On room transition via `process_room_entry`, progressing tropes advance by `passive_progression.rate_per_turn`, reusing `tick_tropes`. Emit OTEL trope-tick span.
2. No double-tick: New per-transition tick does not compound the existing per-interaction tick. Which-fires-when rule is explicit and tested.
3. Idempotent re-entry: Re-entering an already-discovered room does not re-tick/re-deplete (pin the rule; test both directions).
4. Item resource depletion: Items with finite `uses_remaining` decrement on movement trigger; at zero, marked exhausted (don't silently delete).
5. OTEL observability: Trope-tick span on transition + resource-depletion span (`item`, `before`, `after`). Skip-reason if no action taken (never silent partial).

### Files to Modify

Per context file:
- `sidequest/game/room_movement.py` — `process_room_entry` transition hook
- `sidequest/game/trope_tick.py` — reuse `tick_tropes`; possibly transition-mode entry
- Item depletion: `narration_apply.py` and/or `room_movement.py`
- `sidequest/telemetry/` — add transition-tick + depletion spans

### Key Constraints

- **Room-graph mode only** (not region-mode cartography)
- **No double-tick** against per-interaction tick
- **Idempotent** — re-entry to discovered room must follow explicit rule
- **No silent fallbacks** — if depletion can't resolve trigger class, fail loud
- **Wiring required** — prove end-to-end via fixture-driven behavior + OTEL assertions, not grep wiring tests

### Test Guidance (TEA Red Phase)

From context file:
- Fixture-driven behavior test: room-graph genre pack + snapshot with progressing trope + torch; drive transition through real `process_room_entry`; assert trope advanced once + torch decremented once + both spans fired. Canonical shape: `tests/server/test_location_description_emit.py`
- No-double-tick test: single room-graph turn with transition + interaction loop advances trope exactly once
- Idempotent re-entry test: re-entering discovered room does not re-tick/re-deplete (or does, per pinned rule)
- Region-mode regression: region traversal still does NOT fire these

## Workflow Tracking

**Workflow:** tdd (phased)
**Phase:** finish
**Phase Started:** 2026-05-28T18:17:58Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T16:35:00Z | 2026-05-28T16:43:21Z | 8m 21s |
| red | 2026-05-28T16:43:21Z | 2026-05-28T18:00:08Z | 1h 16m |
| green | 2026-05-28T18:00:08Z | 2026-05-28T18:08:16Z | 8m 8s |
| spec-check | 2026-05-28T18:08:16Z | 2026-05-28T18:10:35Z | 2m 19s |
| verify | 2026-05-28T18:10:35Z | 2026-05-28T18:12:06Z | 1m 31s |
| review | 2026-05-28T18:12:06Z | 2026-05-28T18:16:50Z | 4m 44s |
| spec-reconcile | 2026-05-28T18:16:50Z | 2026-05-28T18:17:58Z | 1m 8s |
| finish | 2026-05-28T18:17:58Z | - | - |

## Sm Assessment

Setup complete, routing to TEA (red phase). Story 71-15 wires two ADR-055 gaps confirmed
unwired in the 2026-05-02 status: per-transition trope tick (`tick_on_room_transition`
nonexistent) and item resource depletion on movement (`uses_remaining` written, never
decremented). ACs are NOT in sprint YAML — they are derived in this session file from the
context doc (`sprint/context/context-story-71-15.md`) and ADR-055's 2026-05-28 amendment;
TEA must read both before writing failing tests.

Scope guardrails pinned for TEA/Dev: room-graph mode only (region/cartography unaffected),
no double-tick against the existing per-interaction tick, idempotent re-entry, fail-loud on
unresolvable depletion triggers (No Silent Fallbacks), and end-to-end wiring proven via
fixture-driven behavior + OTEL span assertions — not grep wiring tests. Single repo:
sidequest-server, branch `feat/71-15-room-graph-movement-trope-item-tick` off develop.

No code read or implementation planned by SM — that is TEA's and Dev's lane.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-pt behavior story wiring two unwired mechanics; behavior must be pinned before implementation.

**Test Files:**
- `sidequest-server/tests/server/test_71_15_room_graph_movement_side_effects.py` — 8 tests across 5 ACs + region-mode regression, driving the real `_execute_narration_turn` → `_apply_narration_result_to_snapshot` location seam (modeled on `test_45_27_trope_tempo_wire.py`).

**Tests Written:** 8 tests covering 5 ACs
**Status:** RED — 5 failing (behavior unwired), 3 passing invariant guards

RED breakdown (verified via focused `uv run pytest … -n0`, DB URL set):
- AC1/AC5 `test_room_graph_transition_emits_transition_tick_span` — FAIL (no `room.transition_tick` span)
- AC1/AC5 `test_transition_tick_span_names_the_advanced_trope` — FAIL (no span)
- AC4 `test_torch_decrements_once_on_transition` — FAIL (`uses_remaining` not decremented)
- AC5 `test_depletion_span_carries_before_and_after` — FAIL (no `item.resource_depleted` span)
- AC4 `test_torch_marked_exhausted_at_zero_not_deleted` — FAIL (`uses_remaining` stays 1, no `exhausted` flag)

Passing invariant guards (correct today; they pin rules Dev must not break):
- AC2 `test_transition_turn_advances_trope_exactly_once` (no-double-tick)
- AC3 `test_reentering_same_room_fires_no_transition_spans` (idempotent re-entry)
- Region regression `test_region_mode_location_change_fires_nothing`

### Rule Coverage

Source: `.pennyfarthing/gates/lang-review/python.md`. Behaviour-testable rules for
this story are covered; the rest are Dev-implementation concerns the linter/Reviewer
enforces (not behaviour-assertable in RED).

| Rule | Test(s) | Status |
|------|---------|--------|
| Test quality — meaningful assertions, no vacuous truthy | all 8 (assert on concrete values: `uses_remaining==2`, `before==3`) | enforced |
| No Silent Fallbacks — no silent delete at exhaustion | `test_torch_marked_exhausted_at_zero_not_deleted` | failing (RED) |
| Observability — every subsystem decision emits a span (no silent partial) | transition-tick + depletion span tests | failing (RED) |
| Mode-gated behaviour (no cross-mode leakage) | `test_region_mode_location_change_fires_nothing` | passing guard |

**Rules checked:** 4 of the lang-review checklist's behaviour-testable rules have coverage; bare-except / mutable-default / type-annotation / async-await / resource-leak rules are Dev-implementation concerns the linter + Reviewer catch, not RED-testable for this story.
**Self-check:** 0 vacuous assertions — every test asserts a concrete value or a span-presence/absence with a diagnostic message.

**Handoff:** To Dev (Inigo) for GREEN. Wire into the narration-apply location seam, NOT `process_room_entry` (see Delivery Findings + Design Deviations).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | success | 0 smells; 8/8 story green; 7 known pre-existing confirmed unchanged | confirmed 0, dismissed 0, deferred 0 (2 probes → addressed as VERIFIED below) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 enabled returned; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 2 confirmed (both Medium/Low, non-blocking — my own analysis), 0 dismissed, 2 deferred (folded into Architect follow-up)

## Reviewer Assessment

**Verdict:** APPROVED (no Critical/High; two non-blocking findings documented + deferred)

### Observations

- **[MEDIUM] AC3 may be contradicted, not just under-tested** — `narration_apply.py` transition gate is `result.location != old_loc`, so moving *back into an already-`discovered` room* still ticks + depletes. AC3 literally says "Re-entering an already-`discovered` room does not re-tick/re-deplete **unless ADR-055 specifies a re-entry cost**." TEA tested only the no-move direction (re-narrating the current room); the discovered-room-backtrack direction the context explicitly asked to "test both directions" was neither tested nor decided. The code's "every transition costs" reading is realistic dungeon pacing but may contradict AC3's literal default. Non-blocking (behavior is well-defined; the clearest "idempotent" case works), but must be explicitly resolved.
- **[LOW] MP depletion is actor-only** — `_apply_room_graph_transition_effects` depletes only the acting PC's inventory. Co-located PCs who follow via scene-cohort propagation (`narration_apply.py`:~1782) don't burn their own light source. Unspecified by the story (single-PC tested). Deferred.
- **[VERIFIED] No double-tick** — the helper emits `room.transition_tick` over `[t.id … status=="progressing"]` and performs NO advance; the only trope advance is the per-turn `tick_tropes` (websocket_session_handler.py:1052). Regardless of apply-vs-tick ordering within the turn, total advance is one. Complies with AC2.
- **[VERIFIED] No silent delete** — exhausted items set `item["exhausted"]=True` and remain in `inventory.items` (narration_apply helper). Complies with No Silent Fallbacks. Corroborated by reviewer-security.
- **[VERIFIED] Region-mode gated** — `if … snapshot.discovered_rooms …` short-circuits when empty; region-mode location changes never reach the helper. Matches AC "room-graph only".
- **[VERIFIED] OTEL routing** — both `SPAN_ITEM_RESOURCE_DEPLETED` and `SPAN_ROOM_TRANSITION_TICK` registered in `SPAN_ROUTES`; `test_routing_completeness` passes. Complies with the OTEL mandate.
- **[VERIFIED] Mutation persistence** (preflight probe) — the helper mutates the live snapshot's inventory dicts in place, the same pattern every other apply-pipeline mutation uses (`character_locations`, etc.); the turn-end save serializes that snapshot. Correct and intended.
- **[VERIFIED] [SEC] Security** — reviewer-security returned clean: no injection (no eval/exec/subprocess/yaml.unsafe_load/pickle), no secret/PII in span attributes (item ids, counts, room/PC names — table-visible game state), no auth boundary crossed, otel_capture fixture tears down its span processor in `finally`. Confirmed against the diff.

### Rule Compliance

Project rules applied to the changed code (CLAUDE.md / SOUL.md / lang-review python.md):
- **No Silent Fallbacks** — depletion: exhausted flagged, not deleted (compliant); `character is None` early-return is a clean no-apply, not a masked error (compliant); `uses is None or uses <= 0` skips non-finite/spent items without inventing a default (compliant).
- **No Stubbing / No half-wired** — helper has a real production caller (the location branch); spans registered + asserted. Compliant.
- **Every test suite needs a wiring test** — the 8 tests drive the real `_execute_narration_turn` seam with OTEL-span + state assertions (no source-text grep). Compliant.
- **OTEL observability** — both subsystem decisions emit spans. Compliant.
- **Mutable default args / bare except / type annotations** (lang-review #2/#1/#3) — helper has full annotations, no mutable defaults, no try/except. Compliant.

### Devil's Advocate

Argue the code is broken. First, the AC3 contradiction is the sharpest blade: a player exploring a megadungeon who steps back into a corridor they cleared ten turns ago burns another torch-use and nudges the Keeper closer — yet AC3 says discovered-room re-entry "does not re-tick/re-deplete." If Keith intended backtracking to be free (the classic "you know this ground, move fast" pacing), this implementation actively punishes it, and no test would catch the regression because TEA only pinned the no-move case. A confused player would notice their torch draining faster than the dungeon's room count justifies. Second, the multiplayer hole: a four-PC party descending together moves as a scene cohort, but only the narrator's "acting character" burns light — so three players' torches are magically inexhaustible while one bears the whole cost, an immersion break a mechanics-first player (Sebastien/Jade) would flag instantly. Third, a malicious or odd content author could seed an item dict with `uses_remaining` as a string ("3"); `uses <= 0` would raise `TypeError` mid-turn and abort the apply pipeline — though this is internal seeded data (chargen_loadout yields ints), and No-Silent-Fallbacks argues against a defensive coercion, so it stays a theoretical edge. Fourth, the gate trusts `discovered_rooms` non-emptiness as the room-graph signal; a future region-mode world that ever populates that list would silently start depleting torches — the Architect already logged this as a Gap. Fifth, a stressed save path that re-hydrates from a snapshot copy rather than the live object would drop the decrement — but preflight and I both traced that the live snapshot is the saved object, so it holds. Net: the genuine concerns (AC3 semantics, MP scope) are spec-decision gaps, not correctness bugs in the tested contract. They are loud, documented, and deferred — not silently shipped.

### Deviation Audit

All TEA + Dev logged deviations reviewed:
- TEA's six contract-pins (seam correction, room-graph dual-signal, no-double-tick, exhausted-state, movement-consumed scope, span names) → ✓ ACCEPTED — each is sound and matches the code.
- Dev's two (transition span does not re-invoke `tick_tropes`; discovered_rooms gate) → ✓ ACCEPTED — the no-re-invoke choice is the correct resolution of the AC1/AC2 tension; the gate choice is pragmatic and already flagged for a durable fix.
- Architect's AC1 movement-gating deferral → ✓ ACCEPTED — sound; the AC3 finding below is the same design cluster and should fold into that follow-up.

**Data flow traced:** narrator `result.location` → `_apply_narration_result_to_snapshot` (old_loc vs new) → `_apply_room_graph_transition_effects` → mutates `character.core.inventory.items[*]["uses_remaining"]` + emits spans → snapshot saved at turn end. Safe: internal state only, no untrusted input.

**Handoff:** To The Man in Black (Architect) for spec-reconcile. The two findings below are non-blocking and recommended for the deferred room-graph-progression follow-up.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Method:** Direct Opus review (right-sized — implementation diff is ~185 LOC across 3 source files: one helper + two span definitions that mirror existing module patterns). Three-teammate haiku fan-out would be ceremony out of proportion to a small, pattern-following addition.

| Lens | Status | Notes |
|------|--------|-------|
| reuse | clean | Span helpers mirror `movement_resolved_span` / `inventory_narrator_extracted_span` exactly (Span.open + SpanRoute). Transition helper reuses `snapshot.active_tropes` + `character.core.inventory.items`; no new abstraction, no duplication. |
| quality | clean | Clear names; docstrings carry the WHY (no-double-tick, no-silent-delete); no dead code. The `item.get("id") or item.get("name") or "unknown"` fallback is intentional and bounded. |
| efficiency | clean | Single linear party scan + single inventory pass; no over-engineering. Empty `progressing` list still fires the transition span by design (AC5: span on every transition). |

**Applied:** 0 fixes (code already minimal and pattern-conforming)
**Flagged for Review:** 0
**Reverted:** 0
**Overall:** simplify: clean

**Quality Checks:** Story suite 8/8 green and `ruff`/`pyright` clean as of green phase; no code changed during verify, so state is unchanged. Full-suite baseline carries 7 pre-existing failures (61-17 cache test via draft PR #499; epic-64 namegen/validator) — none introduced by this story.

**Handoff:** To Westley (Reviewer) for code review. Note the Architect's deferred AC1 movement-gating finding for review context.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (one Major, one Trivial)
**Mismatches Found:** 2

- **AC1 trope progression is not movement-gated** (Ambiguous spec — Behavioral, Major)
  - Spec: AC1 "On a room transition … progressing tropes advance once by `rate_per_turn` (reusing `tick_tropes`), in room-graph mode only"; Assumptions "once-per-transition tick **equivalent to the per-turn tick, not additive**." Read with the "Why This Matters" framing (pressure *through traversal*), the intent is that in room-graph mode progression is driven by movement.
  - Code: the per-turn `tick_tropes` (websocket_session_handler.py:1052) still fires **every turn, ungated by navigation mode**. `_apply_room_graph_transition_effects` adds a `room.transition_tick` correlation span on moves but performs no advance. Net: tropes advance every room-graph turn (move or not); the transition only *labels* the move turns.
  - Recommendation: **D — Defer.** The tested contract (TEA's RED suite — the binding spec per the authority hierarchy) is fully met: exactly one tick on a transition turn (AC2), span fires (AC1/AC5). True movement-gating means suppressing the per-turn tick in room-graph mode and letting the transition own the advance — a behavior change to a shared hot path (every genre's per-turn cadence) with real regression surface, and a pacing decision that belongs to Keith (forever-GM, dungeon-pacing-sensitive). Item depletion — the concrete "consequence of movement" — is fully delivered, so the story's anti-"consequence-free movement" goal is materially advanced. File a follow-up: *"room-graph trope progression movement-gating — suppress per-turn tick in room_graph mode, advance on transition only"* + a TEA test asserting a non-move room-graph turn does NOT advance a progressing trope.

- **AC5 skip-path emits nothing rather than an explicit skip-reason span** (Different behavior — Behavioral, Trivial)
  - Spec: AC5 "On a skip (region mode / no progressing tropes / no depletable items) emit nothing **or** an explicit skip reason; never a silent partial."
  - Code: region mode and no-depletable-items take the "emit nothing" branch (gate short-circuits / loop finds nothing). No silent *partial* occurs.
  - Recommendation: **A — Accept.** AC5 explicitly permits "emit nothing"; the partial-emission hazard it guards against does not arise here. A skip-reason span would aid GM-panel legibility but is not required.

**Decision:** Proceed to review (TEA verify). The Major item is an ambiguous-spec gap whose tested contract passes and whose concrete half (depletion) is delivered; it is deferred with a precise follow-up, not hand-back. Architectural note: this is also recorded as a Dev Question finding and will be carried into spec-reconcile.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/narration_apply.py` — new `_apply_room_graph_transition_effects` helper + a gated call in the `if result.location:` branch (room-graph nav via `discovered_rooms` non-empty + genuine `old != new` transition). NOT routed through `process_room_entry`.
- `sidequest/telemetry/spans/movement.py` — `SPAN_ROOM_TRANSITION_TICK` (`room.transition_tick`) constant + route + `room_transition_tick_span` helper.
- `sidequest/telemetry/spans/inventory.py` — `SPAN_ITEM_RESOURCE_DEPLETED` (`item.resource_depleted`) constant + route + `item_resource_depleted_span` helper.
- `tests/server/test_71_15_room_graph_movement_side_effects.py` — TEA's tests (RED → GREEN; lint fix only).

**Tests:** 8/8 story tests GREEN. Full server suite: 7570 passed, 7 pre-existing failures (61-17 `test_zones_carry_cache_boundary_flag` via draft PR #499; epic-64 namegen-corpus + pack-validator) — all in unrelated subsystems, zero introduced. `ruff` clean; `pyright` introduces 0 new errors (the 28 in narration_apply.py are pre-existing `result: object` typing, none in my line ranges).
**Branch:** feat/71-15-room-graph-movement-trope-item-tick (pushed)

**Wiring proof:** behavior + OTEL-span assertions through the real `_execute_narration_turn` → `_apply_narration_result_to_snapshot` path (no source-text grep). New code has a non-test consumer (the location branch).

**Handoff:** To Fezzik (TEA) for verify/simplify, then Westley for review.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

### TEA (test design)

- **Conflict** (non-blocking): The context doc's pinned seam is factually wrong — it names `process_room_entry` (room_movement.py:59) as the "idempotent, records-visited-room" transition hook, but that function is a chassis/intimate-confrontation auto-fire hook that early-returns for non-chassis rooms and records a cooldown stamp, not `discovered_rooms`. The promised `validate_room_transition`/`apply_validated_move` functions never landed.
  Affects `sidequest/server/narration_apply.py` (wire the per-transition tick + depletion into the `if result.location:` branch at ~:1734, move = `old_loc != result.location`; or a helper it calls — NOT `process_room_entry`).
  *Found by TEA during test design.*
- **Gap** (non-blocking): The narration-apply seam currently has no active-world context, so there is no existing signal for "room-graph mode" at the point the tick/depletion must gate. Dev must thread the world's `cartography.navigation_mode` (or add an explicit `snapshot.navigation_mode`) to the seam.
  Affects `sidequest/server/narration_apply.py` / `sidequest/server/websocket_session_handler.py` (provide room-graph mode to the apply path).
  *Found by TEA during test design.*

### Dev (implementation)

- **Question** (non-blocking): In room-graph mode the per-turn `tick_tropes` still advances progressing tropes every turn (including non-move turns); this story only adds the movement-correlation span, not movement-*only* progression. The context's "pressure through traversal" framing may intend that a non-moving dungeon turn should NOT escalate the Keeper. No AC/test requires suppressing the per-turn tick, so it was left intact (minimal change).
  Affects `sidequest/server/websocket_session_handler.py` (`_execute_narration_turn` per-turn `tick_tropes` call) — Architect should decide whether room-graph progression is movement-gated.
  *Found by Dev during implementation.*
- **Gap** (non-blocking): The room-graph gate uses `snapshot.discovered_rooms` non-empty (the room-graph state container, populated only in room_graph mode) rather than threading `cartography.navigation_mode` to the apply seam — the seam still has no world context. Functionally correct today, but a dedicated `snapshot.navigation_mode` field would be cleaner and survive a future region-mode world that also populates `discovered_rooms`.
  Affects `sidequest/server/narration_apply.py` (transition gate) — closes TEA's Gap finding pragmatically; an explicit mode field is the durable fix.
  *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

### TEA (test design)

- **Tests target `_apply_narration_result_to_snapshot`, not `process_room_entry`**
  - Spec source: context-story-71-15.md, "Root cause / current state" §1 + "Files to Modify"
  - Spec text: "The transition seam where it belongs is `room_movement.py:59` `process_room_entry` (idempotent — it records the visited room, so it is the natural once-per-transition hook)."
  - Implementation: RED tests drive the real production move seam — the `if result.location:` branch in `_apply_narration_result_to_snapshot` (narration_apply.py:1734), move detected as `old_loc != result.location`.
  - Rationale: Verified against HEAD — `process_room_entry` is a chassis/intimate-confrontation auto-fire hook that early-returns for non-chassis rooms and records a *cooldown stamp*, not `discovered_rooms`. The promised `validate_room_transition`/`apply_validated_move` functions never landed. Hooking `process_room_entry` would no-op for ordinary room-graph rooms.
  - Severity: major
  - Forward impact: Dev must wire the tick + depletion into the narration-apply location branch (or a helper it calls), not into `process_room_entry`. See Delivery Finding.

- **Room-graph mode signalled two ways in fixtures (gate mechanism left to Dev)**
  - Spec source: context-story-71-15.md, Constraints "Room-graph mode only"
  - Spec text: "These mechanics fire under `NavigationMode` room-graph traversal, NOT region-mode cartography."
  - Implementation: tests set room-graph mode by both seeding `snapshot.discovered_rooms` AND flipping any loaded world's `cartography.navigation_mode`; region tests set neither.
  - Rationale: the apply seam has no world context today, so the exact gate signal is a Dev decision. Signalling both makes the suite pass under either choice without coupling to one.
  - Severity: minor
  - Forward impact: if Dev adds an explicit `snapshot.navigation_mode` field instead, update `_enter_room_graph_mode` to set it too.

- **No-double-tick rule pinned as "transition tick replaces the per-turn tick" (one tick total)**
  - Spec source: context-story-71-15.md, AC2 + Assumptions
  - Spec text: "The new per-transition tick does not compound the existing per-interaction tick … once-per-transition tick equivalent to the per-turn tick, not additive."
  - Implementation: `test_transition_turn_advances_trope_exactly_once` asserts a transition turn advances a progressing trope by exactly one tick's delta.
  - Rationale: Architect's reading (equivalent, not additive) governs per context. This guard passes today (only the per-turn tick fires) and fails if Dev wires the transition tick additively.
  - Severity: minor
  - Forward impact: none if Dev follows the equivalent-not-additive reading.

- **Exhausted state pinned to `uses_remaining == 0` + `exhausted=True` flag (no delete)**
  - Spec source: context-story-71-15.md, AC4
  - Spec text: "at zero, the item is marked exhausted (define the exhausted state; do not delete the item silently)."
  - Implementation: `test_torch_marked_exhausted_at_zero_not_deleted` asserts `uses_remaining == 0` and `item["exhausted"] is True`, item still in inventory.
  - Rationale: AC4 explicitly defers the representation to the implementer; this is the simplest non-deleting marker on the runtime item dict.
  - Severity: minor
  - Forward impact: if Dev models exhaustion differently (e.g. a separate status), update the AC4 assertion in the same PR.

- **Movement-consumed items = any item with finite `uses_remaining` (torch model)**
  - Spec source: context-story-71-15.md, AC4 + Assumptions
  - Spec text: "Items carrying a finite `uses_remaining` … decrement on the ADR-055 movement trigger"; "Depletion trigger for non-movement-consumed items … is OUT of scope."
  - Implementation: tests deplete any inventory item dict carrying a non-None `uses_remaining` by one per transition; ability-charge depletion not tested.
  - Rationale: scopes to the torch model the context names as in-scope; broader trigger taxonomy is deferred.
  - Severity: minor
  - Forward impact: none — matches the context's stated scope.

- **OTEL span names pinned: `room.transition_tick` and `item.resource_depleted`**
  - Spec source: context-story-71-15.md, AC5
  - Spec text: "a trope-tick span on transition and a resource-depletion span (`item`, `before`, `after`)."
  - Implementation: tests assert spans named `room.transition_tick` (carrying the advanced trope id) and `item.resource_depleted` (carrying `item`/`before`/`after`).
  - Rationale: AC5 mandates spans but not names; concrete names are needed to assert on them.
  - Severity: minor
  - Forward impact: if Dev chooses other names, rename in these tests in the same PR.

### Dev (implementation)

- **Transition tick emits a correlation span; it does NOT re-invoke `tick_tropes`**
  - Spec source: context-story-71-15.md, AC1
  - Spec text: "On a room transition … progressing tropes advance once by their `passive_progression.rate_per_turn` (reusing `tick_tropes`)."
  - Implementation: `_apply_room_graph_transition_effects` emits `room.transition_tick` carrying the currently-progressing trope ids but performs NO trope advance. The single advance is the existing per-turn `tick_tropes` call in `_execute_narration_turn`; the span correlates that advance with the transition that earned it.
  - Rationale: re-invoking `tick_tropes` on the transition would double-advance against the per-turn tick, violating AC2 (no-double-tick) and `test_transition_turn_advances_trope_exactly_once`. AC1's "advance once" is satisfied by the per-turn tick; AC2 is the binding constraint. Honest per the OTEL mandate — the tropes genuinely progressed this turn.
  - Severity: minor
  - Forward impact: see Delivery Finding (Question) — if Architect decides room-graph progression must be movement-*only*, the per-turn tick would be suppressed in room-graph mode and this helper would own the advance; the span/test contract is unaffected.
  - Spec authority: AC2 (story context) outranks the AC1 "reusing tick_tropes" phrasing where they tension; logged before implementing.

- **Room-graph gate uses `discovered_rooms` non-empty (not threaded `navigation_mode`)**
  - Spec source: context-story-71-15.md, Constraints "Room-graph mode only"
  - Spec text: "These mechanics fire under `NavigationMode` room-graph traversal, NOT region-mode cartography."
  - Implementation: gate is `bool(snapshot.discovered_rooms)` at the apply seam.
  - Rationale: `discovered_rooms` is populated only by `init_room_graph_location` (room_graph mode), so non-empty ⟺ room-graph session; the seam has no world context to read `cartography.navigation_mode` without new plumbing (minimal change). Matches TEA's dual-signal fixture.
  - Severity: minor
  - Forward impact: a future region-mode world that populates `discovered_rooms` would wrongly trip the gate — see Delivery Finding (Gap); durable fix is an explicit `snapshot.navigation_mode`.

### Reviewer (audit)

- **Discovered-room re-entry charges a cost (possible AC3 contradiction)**
  - Spec source: context-story-71-15.md, AC3
  - Spec text: "Idempotent re-entry: Re-entering an already-`discovered` room does not re-tick/re-deplete unless ADR-055 specifies a re-entry cost (pin the rule; test both directions)."
  - Implementation: the transition gate is `result.location != old_loc`, so moving back into a room already in `discovered_rooms` IS a transition → it ticks (span) and depletes. TEA tested only the no-move direction (re-narrating the current room); the discovered-room-backtrack direction was neither tested nor explicitly decided.
  - Rationale: "every transition costs" is realistic dungeon pacing and internally consistent, but AC3's literal default reads the opposite (discovered-room re-entry is free). Genuine ambiguity in AC3 itself ("unless ADR-055 specifies a re-entry cost"); ADR-055 does not pin it. Non-blocking — the clearest "idempotent" case (no-move) works and is tested.
  - Severity: medium
  - Forward impact: Resolve in the deferred room-graph-progression follow-up — decide whether backtracking into a discovered room costs, add a test for that second direction, and (if free) add `to_room not in discovered_rooms` to the gate.

- **MP depletion is actor-only**
  - Spec source: context-story-71-15.md, Scope ("as the party moves") + AC4
  - Spec text: "resource depletion (the canonical 'torch burn') as the party moves through a dungeon."
  - Implementation: `_apply_room_graph_transition_effects` depletes only the acting PC's inventory; co-located PCs who follow via scene-cohort propagation do not burn their own light source.
  - Rationale: story tested single-PC only; MP depletion semantics (shared light vs per-PC) were never specified.
  - Severity: low
  - Forward impact: Decide MP depletion model (single shared source vs per-PC) in the deferred follow-up; out of scope for the single-PC contract delivered here.

### Architect (reconcile)

Reviewed all prior entries (TEA ×6, Dev ×2, Reviewer ×2): spec sources resolve to real
docs (`sprint/context/context-story-71-15.md`, ADR-055), quoted spec text is accurate,
implementation descriptions match the merged code, and forward-impact lines are correct.
No corrections needed; all six fields present on every entry.

- **No additional deviations found** beyond those already logged. The story's delivered surface is sound and matches the tested contract.

**AC accountability (no formal deferral table — ACs derived from context):**
- AC2 (no-double-tick), AC4 (item depletion + exhausted-at-zero, no delete), AC5 (both OTEL spans): **DONE** — fully delivered and tested.
- AC3 (idempotent re-entry): **PARTIAL** — the no-move direction is done+tested; the "backtrack into an already-discovered room" direction is undecided/untested (Reviewer audit, Medium).
- AC1 (per-transition trope tick): **PARTIAL/DEFERRED** — observability span delivered; movement-*gated* progression (suppress per-turn tick in room-graph mode) not implemented (Architect spec-check, Major).

**Consolidated follow-up recommendation (for the boss):** Three deferred items are one design
cluster — *"what does room-graph traversal cost, and for whom?"* File a single follow-up
story: **room-graph traversal-cost semantics** covering (1) movement-gated trope progression
(suppress the per-turn `tick_tropes` in room_graph mode so non-move turns don't escalate);
(2) whether backtracking into a discovered room costs (gate on `to_room not in
discovered_rooms` if free, else keep current "every transition costs" + add the AC3 second-
direction test); (3) MP depletion model (shared light source vs per-PC). All three are
Keith/pacing decisions, not code bugs — this story correctly ships the observability + the
single-PC torch-burn + the no-double-tick guarantee, materially ending "consequence-free
movement," and leaves the pacing-policy questions to an explicit decision.