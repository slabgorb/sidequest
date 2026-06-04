---
story_id: "59-35"
jira_key: ""
epic: "59"
workflow: "tdd"
---
# Story 59-35: Seat present FRIENDLY companions as side=player combatants in confrontations (ADR-116 / Guitar Solo)

## Story Details
- **ID:** 59-35
- **Jira Key:** (not applicable — no Jira integration)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T23:05:37Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T00:00:00Z | 2026-06-04T22:04:32Z | 22h 4m |
| red | 2026-06-04T22:04:32Z | 2026-06-04T22:16:37Z | 12m 5s |
| green | 2026-06-04T22:16:37Z | 2026-06-04T22:30:10Z | 13m 33s |
| review | 2026-06-04T22:30:10Z | 2026-06-04T22:41:13Z | 11m 3s |
| red | 2026-06-04T22:41:13Z | 2026-06-04T22:46:19Z | 5m 6s |
| green | 2026-06-04T22:46:19Z | 2026-06-04T22:52:13Z | 5m 54s |
| review | 2026-06-04T22:52:13Z | 2026-06-04T23:05:37Z | 13m 24s |
| finish | 2026-06-04T23:05:37Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings during setup.

### TEA (test design)

- **Question** (non-blocking): AC1's "not withdrawn" qualifier references a field that does not exist on `Npc`. `withdrawn` is an `EncounterActor` field (`game/encounter.py:125`), not a roster-`Npc` field — a `snapshot.npcs` entry has no `withdrawn` attribute. The friendly-seater scans `snapshot.npcs`, so "not withdrawn" has no direct referent there. Affects `sidequest/server/dispatch/encounter_lifecycle.py` (Dev must decide the intended semantics — likely a no-op for v1, since a roster NPC is not a seated-then-withdrawn actor; or skip an NPC already seated-and-withdrawn in the active encounter). I omitted a test for this leg rather than pin a non-existent field. *Found by TEA during test design.*
- **Gap** (non-blocking): the existing opponent fallback (`_npc_fallback_at_location`, `adversarial=True`) seats EVERY same-location NPC as `side="opponent"` with no disposition filter, so an empty-`npcs_present` combat with a co-located FRIENDLY ally conscripts that ally as the enemy. The friendly-seater must reconcile this. Architect (White Queen, 2026-06-04) recommends the reuse-first fix: teach `_npc_fallback_at_location` to skip `Attitude.FRIENDLY` NPCs rather than build a separate reconciliation pass. Affects `sidequest/server/dispatch/encounter_lifecycle.py:466` (`_npc_fallback_at_location`) and the new `_friendly_fallback_at_location`. Pinned by the failing test `test_friendly_ally_not_conscripted_as_opponent_when_room_sourced`. *Found by TEA during test design.*
- **Question** (non-blocking): AC2 seeding-channel semantics. The existing seeding helpers (`_seed_combat_hp_depletion_to_npcs`, `_publish_combat_edge_to_npcs`) both `continue` on `actor.side != "opponent"`, so they will not arm a `side="player"` ally. My AC2 test asserts the ally RETAINS its own real `Npc.core` HP block (per the design's "no placeholder, no new data model, reuse existing `Npc.core` HP") rather than receiving the opponent's content stats. If Dev instead extends the seeding helpers to derive a player-side pool for allies, the `core.hp.max == 12` assertion in `test_friendly_ally_armed_with_real_stat_block_in_hp_depletion_combat` will need revisiting. Affects `sidequest/server/dispatch/encounter_lifecycle.py` (the two seeding helpers). *Found by TEA during test design.*

### TEA (rework — round-trip 1)

Addressed the Reviewer's REJECT (test-side). Test suite is now 9 tests (was 8); RED with 1 failing, 8 passing (testing-runner `59-35-tea-rework-red`):
- **AC3 added** — `test_friendly_ally_alone_still_raises_no_opponent` (the missing ADR-116 invariant guard). Passes (code already correct).
- **AC4 hardened** — assert `participant.joined` carries `disposition_attitude='friendly'` + `last_seen_turn==2`. The `disposition_attitude` assertion FAILS (RED) — the impl emits only `last_seen_turn`; this drives Dev to add `disposition_attitude` to the friendly seat's span.
- **Vacuous negatives hardened** — `test_absent_`/`test_neutral_` now seat a same-location FRIENDLY control so location/disposition is the proven discriminator (no longer pass against a no-op seater).
- **`armor_class >= 1` → `== 10`** — proves the player-side AC is not clobbered by `_seed_combat_hp_depletion_to_npcs`.
- **Tautology removed** — `test_present_hostile` now asserts `_player_side_names == {PC}` (independent check).
- **Stale test docstrings fixed** — RED-preamble + the wrong seater-placement claim.

**Remaining for Dev (green):** (1) emit `disposition_attitude` on the friendly `participant.joined` span (RED driver); (2) refresh the `_npc_fallback_at_location` docstring's "Side:" paragraph to note the FRIENDLY exclusion; (3) annotate `_friendly_fallback_at_location -> list[NpcMention]` (+ `friendly_allies: list[NpcMention]`). Items (2)/(3) are the Reviewer's LOW source-side findings.

- No new upstream findings during rework. *Found by TEA during test design (rework).*

### Dev (implementation)

- **Improvement** (non-blocking): a friendly NPC ally is seated as a `side="player"` combatant but (a) does NOT roll SWN initiative (no ability scores) and (b) is not armed by the opponent seeding helpers (keeps its own `Npc.core` HP). For v1 the ally acts on narrator beats like an opponent NPC. A follow-up could give NPC allies SWN stat blocks + server-driven turns so they take independent initiative slots. Affects `sidequest/server/dispatch/encounter_lifecycle.py` (`_roll_and_persist_initiative`, the seeding helpers). *Found by Dev during implementation.*
- **Resolved** TEA's three findings: (1) "not withdrawn" → implemented as a no-op (non-existent `Npc` field); (2) opponent-fallback collision → fixed per the Architect's reuse-first recommendation (skip `Attitude.FRIENDLY` in `_npc_fallback_at_location`); (3) AC2 seeding-channel → "retain own block" (helpers stay opponent-only). All three logged as Dev deviations. *Found by Dev during implementation.*

### Dev (rework — round-trip 1)

Addressed the Reviewer's REJECT (source-side) after TEA hardened the tests:
- **AC4 closed** — `participant.joined` now carries `disposition_attitude` (the seated NPC's attitude band) for every roster-NPC seat; a friendly_fallback seat reads `disposition_attitude='friendly'`. Makes `test_friendly_seat_emits_participant_joined_span` green. (`encounter_lifecycle.py` span loop.)
- **Stale docstring fixed** — `_npc_fallback_at_location` "Side:" paragraph now notes the Story 59-35 FRIENDLY exclusion ("every hostile/neutral location NPC", not literally every NPC).
- **Annotation tightened** — `_friendly_fallback_at_location -> list[NpcMention]` + `allies`/`friendly_allies` locals (mypy element-type precision; `NpcMention` already imported under TYPE_CHECKING).

**Verification:** 9/9 story tests green (`59-35-dev-rework-green`); 293 passing across encounter/confrontation/SWN/participant suites; full-suite 10 failures all confirmed pre-existing/unrelated. Pyright: 7 errors == develop baseline (zero introduced; all pre-existing debt in untouched code, and pyright is not in the gate). Pushed to `feat/59-35-...` (commit 96ac70b3).
- No new upstream findings during rework. *Found by Dev during implementation (rework).*

### Reviewer (code review)

- **Gap** (blocking): AC4 is incomplete — the friendly `participant.joined` span omits the `disposition_attitude` attribute the story AC4 explicitly requires (it emits only `last_seen_turn`). Affects `sidequest/server/dispatch/encounter_lifecycle.py:1182-1197` (add `disposition_attitude` to the friendly seat's span attrs) and the OTEL test (assert it). *Found by Reviewer during code review.*
- **Gap** (blocking): AC3 (ADR-116 invariant — PC + friendly ally + zero opponents still raises `NoOpponentAvailableError`) has no test. The code is correct but the invariant is unguarded; a regression seating the ally as the Other would pass all 8 tests. Affects `tests/server/dispatch/test_59_35_friendly_companion_seating.py` (add the raise-test). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): three tests are weaker than they read — `test_absent_*`/`test_neutral_*` pass against a no-op seater, `armor_class >= 1` is a floor that can't fail (→ `== 10`), and `test_present_hostile`'s second assertion is tautological. Plus 3 stale comments and a bare-`list` annotation. Affects the test file + `encounter_lifecycle.py` docstrings/annotation. *Found by Reviewer during code review.*

### Reviewer (re-review — round-trip 1, APPROVED)

Both round-1 HIGH blockers verified resolved; rule-checker CLEAN; preflight GREEN. APPROVED. Remaining non-blocking findings for a fast-follow `/chore` (no third round-trip warranted):
- **Improvement** (non-blocking): AC3 test's secondary `if snap.encounter is not None: assert opp` is dead code (raise at `encounter_lifecycle.py:1042` precedes `snapshot.encounter = enc` at :1304); the primary `pytest.raises` already guards the invariant. Replace with `assert snap.encounter is None`. Affects `tests/server/dispatch/test_59_35_friendly_companion_seating.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `test_neutral_npc_not_seated_as_player` asserts player-side absence only; add `assert _actor(enc, "Bystander") is None` for full-absence (currently passes — strengthening, not a live bug). Affects the test file. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): 4 per-test docstrings + the module Background still use pre-implementation present tense ("Today … is never seated"), and the `disposition_attitude` source comment over-scopes (the attr rides every roster-NPC seat). Half-finished docstring cleanup. Affects the test file + `encounter_lifecycle.py:~1188`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Omitted the "not withdrawn" AC1 leg from test coverage**
  - Spec source: context-story-59-35.md, AC1
  - Spec text: "It seats snapshot.npcs that are scene-present (is_npc_in_scene) AND disposition.attitude()==Attitude.FRIENDLY AND not withdrawn as EncounterActor(side='player')."
  - Implementation: No test exercises a "withdrawn" predicate. `withdrawn` is an `EncounterActor` field, not an `Npc` field, so a `snapshot.npcs` candidate has no `withdrawn` state to assert against.
  - Rationale: Writing a test that pins `npc.withdrawn` would assert a field the model does not have — a vacuous/incorrect test. The three covered paths (friendly→seated, hostile→not, absent→not) plus the neutral guard fully exercise the disposition + scene-presence predicate, which is the load-bearing logic. Flagged as a Delivery Finding for Dev to resolve the intended semantics.
  - Severity: minor
  - Forward impact: none — no sibling story depends on a withdrawn-roster-NPC path.

- **AC2 asserts the ally retains its OWN stat block, not the opponent's content stats**
  - Spec source: context-story-59-35.md, AC2
  - Spec text: "a friendly-seated NPC in an hp_depletion confrontation has core.hp/armor_class seeded like an opponent."
  - Implementation: `test_friendly_ally_armed_with_real_stat_block_in_hp_depletion_combat` constructs the ally with a distinctive pool (7/12) and asserts that pool survives (max==12) plus a resolvable `armor_class>=1`, rather than asserting the ally received the opponent's `opponent_hp`/`opponent_armor_class` content values.
  - Rationale: "Seeded like an opponent" reads as "armed via the same ADR-114 mechanism with a real (non-placeholder) block", not "given the enemy's numbers" — seeding an ally with the opponent's HP/AC is semantically wrong, and the design explicitly says "reuse existing Npc.core HP, no new data model, no placeholder HP". The test pins the no-placeholder/no-clobber contract behaviourally.
  - Severity: minor
  - Forward impact: none — confined to 59-35's armed-ally contract.

### Dev (implementation)

- **Friendly NPC allies are skipped from SWN initiative**
  - Spec source: context-story-59-35.md, AC1 + AC2
  - Spec text: "seats snapshot.npcs … as EncounterActor(side='player')" / "a friendly-seated NPC … through the SAME paths opponents use".
  - Implementation: `_roll_and_persist_initiative` now `continue`s past a `side="player"` actor that is a roster `Npc` rather than a `Character` (it has no SWN ability scores). Without this, seating an ally on the SWN hp_depletion path raised `ValueError("player actor 'Mara' not found among snapshot.characters")`. The original fail-loud is preserved for a player-side actor that is NEITHER a Character NOR a roster Npc (genuine PC name-skew).
  - Rationale: `CreatureCore`/`Npc` carry no ability scores (documented in `_roll_and_persist_initiative`), so an NPC ally has no DEX to roll 1d8+DEX. v1 seats the ally as a combatant that acts on narrator beats (like an opponent NPC), not on a server-rolled initiative slot. Not a silent fallback — it is the legitimate "NPCs have no SWN scores yet" fact, and PC skew still fails loud.
  - Severity: minor
  - Forward impact: minor — a future story giving NPC allies SWN stat blocks (or server-driven ally turns) would revisit this skip.

- **AC1 "not withdrawn" leg implemented as a no-op**
  - Spec source: context-story-59-35.md, AC1
  - Spec text: "seats snapshot.npcs that are scene-present (is_npc_in_scene) AND disposition.attitude()==Attitude.FRIENDLY AND not withdrawn as EncounterActor(side='player')."
  - Implementation: `_friendly_fallback_at_location` filters on location + `Attitude.FRIENDLY` only; there is no `withdrawn` check. `withdrawn` is an `EncounterActor` field, not an `Npc` field (per TEA's finding), so a `snapshot.npcs` candidate has no withdrawn state.
  - Rationale: a roster NPC is not a seated-then-withdrawn actor — the "not withdrawn" qualifier has no referent at the sourcing layer. Adding a check against a non-existent field would be dead code. The dedup against `already_seated` already prevents re-seating an ally the narrator named.
  - Severity: trivial
  - Forward impact: none.

- **AC2 seeding-channel resolved to "retain own block" (confirms TEA's question)**
  - Spec source: context-story-59-35.md, AC2
  - Spec text: "a friendly-seated NPC … has core.hp/armor_class seeded like an opponent."
  - Implementation: the seeding helpers (`_seed_combat_hp_depletion_to_npcs`, `_publish_combat_edge_to_npcs`) were left opponent-only; a friendly ally keeps its OWN `Npc.core` HP + `armor_class` (default 10) rather than being seeded with the opponent's content stats.
  - Rationale: the design says "reuse existing `Npc.core` HP, no new data model, no placeholder HP" — "seeded like an opponent" means armed via the same ADR-114 mechanism with a real block, not given the enemy's numbers. Seeding an ally with `opponent_hp`/`opponent_armor_class` would be semantically wrong.
  - Severity: minor
  - Forward impact: none — matches TEA's AC2 test (asserts the ally's own 7/12 pool survives).

### Reviewer (audit)

- **TEA: "Omitted the 'not withdrawn' AC1 leg"** → ✓ ACCEPTED by Reviewer: `withdrawn` is verifiably an `EncounterActor` field, not an `Npc` field; testing a non-existent field would be vacuous. Sound.
- **TEA: "AC2 asserts the ally retains its OWN stat block"** → ✓ ACCEPTED by Reviewer: the design says "reuse existing `Npc.core` HP, no placeholder"; "seeded like an opponent" means the mechanism, not the enemy's numbers. Sound. (But see Reviewer finding on the vacuous `armor_class >= 1` assertion — the AC2 test's HP leg is sound, the AC assertion is weak.)
- **Dev: "Friendly NPC allies skipped from SWN initiative"** → ✓ ACCEPTED by Reviewer: confirmed the `continue` is gated on roster membership and preserves the fail-loud for genuine PC name-skew (rule-checker concurred: not a silent fallback). Sound.
- **Dev: "'not withdrawn' implemented as no-op"** → ✓ ACCEPTED by Reviewer: consistent with TEA's finding. Sound.
- **Dev: "AC2 seeding-channel resolved to 'retain own block'"** → ✓ ACCEPTED by Reviewer: matches design intent. Sound.
- **UNDOCUMENTED — friendly-seater placement diverged from the design seam:** the story context design seam says insert the friendly fallback "AFTER opponent fallback (~925) and BEFORE the no-opponent guard (946)". Dev placed it AFTER the no-opponent guard (`encounter_lifecycle.py:~1043`). Not logged by Dev. → ✓ ACCEPTED by Reviewer (functionally equivalent and arguably cleaner: allies are kept OUT of `npcs_present`, so the guard fires identically whether the seater runs before or after it; placing it after avoids computing allies for a confrontation that the guard rejects). Severity: trivial (functional), but the TEST DOCSTRING claims the wrong placement (see Reviewer finding [DOC-3]) and MUST be corrected so it doesn't misdirect maintainers.

## SM Assessment

Story 59-35 selected by user from the available backlog (34 unblocked stories, 153 pts). Setup verified clean for handoff to TEA:

- **Scope is well-bounded and dependency-free.** This story completes the *friendly* half of ADR-116's seating symmetry — the opponent fallback already exists (`_npc_fallback_at_location`), so the work is a parallel `_friendly_fallback_at_location` plus existing-channel reuse. No new data model, no blocked dependencies, no stack parent.
- **Player-value rationale.** Directly enacts the SOUL Guitar Solo principle: allied NPCs at the player's side become concurrent combatants instead of a silent audience. Serves the playgroup's table-coordination need without bending pacing.
- **TDD fit confirmed.** The six ACs each carry concrete test vectors (three-path seater unit test, HP-seeding parity, no-opponent invariant regression, real-OTEL-span assertion for `participant.joined source='friendly_fallback'`, and a wiring test asserting the ally lands in the per-recipient CONFRONTATION frame). The wiring test satisfies CLAUDE.md's "every test suite needs a wiring test" mandate.
- **OTEL coverage planned.** AC4 requires the `participant.joined` span with `source='friendly_fallback'` — the lie-detector hook is part of the contract, not an afterthought.

Session, context (6553 bytes), and branch (`feat/59-35-seat-friendly-companions-player-combatants` on develop in sidequest-server) all present. Routing to TEA for RED.

## TEA Assessment

**Tests Required:** Yes
**Reason:** n/a (behavioral engine change — friendly-seater + OTEL + frame delivery)

**Test Files:**
- `tests/server/dispatch/test_59_35_friendly_companion_seating.py` — 8 tests covering all 5 ACs (AC1 seater + boundaries, AC2 armed stat block, AC4 OTEL span, AC5 frame-delivery wiring) plus the empty-`npcs_present` collision guard the Architect flagged.

**Tests Written:** 8 tests covering 5 ACs (AC3 — the no-opponent invariant — is already pinned by the existing `tests/server/test_chase_opponent_seating.py::test_chase_with_empty_room_raises_no_opponent`; friendly seating never touches the opponent-required guard, so I did not duplicate it. See Rule Coverage note.)
**Status:** RED (confirmed via testing-runner RUN_ID `59-35-tea-red`: 5 failing, 3 passing)

**RED breakdown:**

| Test | AC | State | Fails because |
|------|----|----|----|
| `test_present_friendly_npc_seated_as_player_side` | AC1 | FAIL (RED) | ally never sourced from `snapshot.npcs` — `actors=[Vesh, Raider]` |
| `test_present_hostile_npc_not_friendly_seated` | AC1 | PASS (guard) | no friendly-seater exists to wrongly seat a hostile |
| `test_absent_friendly_npc_not_seated` | AC1 | PASS (guard) | location filter boundary holds vacuously today |
| `test_neutral_npc_not_seated_as_player` | AC1 | PASS (guard) | neutral never auto-seated today |
| `test_friendly_ally_not_conscripted_as_opponent_when_room_sourced` | AC1 | FAIL (RED) | opponent fallback seats the FRIENDLY ally as `opponent` (collision) |
| `test_friendly_seat_emits_participant_joined_span` | AC4 | FAIL (RED) | only `(Vesh,player,seat)` + `(Raider,opponent,router_named)` — no `friendly_fallback` |
| `test_friendly_ally_appears_in_confrontation_payload_actors` | AC5 | FAIL (RED) | payload `actors` omit the ally (never seated) |
| `test_friendly_ally_armed_with_real_stat_block_in_hp_depletion_combat` | AC2 | FAIL (RED) | ally not seated in the real `space_opera` hp_depletion combat |

### Rule Coverage

| Rule (python.md lang-review) | Test(s) | Status |
|------|---------|--------|
| #6 test-quality (no vacuous asserts) | every test asserts specific values (`side=="player"`, named actor presence, `hp.max==12`, span `source=="friendly_fallback"`) — self-checked, no `assert True`/truthy-only checks | enforced |
| #3 type annotations at boundaries | helpers (`_make_npc`, `_snap`, `_spacer`, `_explicit_opponent`) carry full annotations | enforced |

**Rules checked:** 2 of 13 lang-review rules are test-authorable from the test side (the rest — silent-exceptions, mutable-defaults, logging, resource-leaks, async, etc. — apply to Dev's implementation diff and are the green-phase/review concern, not RED-test rubric, since no production source changed in this phase).
**Self-check:** 0 vacuous tests found. The AC2 test was specifically hardened against vacuousness with a distinctive HP pool (7/12) so a no-op seating cannot pass it.

**Wiring test:** `test_friendly_ally_appears_in_confrontation_payload_actors` is the integration/wiring test (CLAUDE.md "Every Test Suite Needs a Wiring Test") — it drives the real `instantiate_encounter_from_trigger` → `build_confrontation_payload` path end-to-end, not a unit mock. AC4's OTEL-span test is a behavior-driven wiring assertion (no source-text grep, per CLAUDE.md "No Source-Text Wiring Tests").

**Three Delivery Findings logged** (see above) — the "not withdrawn" non-existent-field question, the opponent-fallback collision (Architect's reuse-first fix: skip FRIENDLY in `_npc_fallback_at_location`), and the AC2 seeding-channel semantics question.

**Handoff:** To Dev (White Rabbit) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/dispatch/encounter_lifecycle.py` — added `_friendly_fallback_at_location` (symmetric friendly-seater, `side="player"`); taught `_npc_fallback_at_location` to skip `Attitude.FRIENDLY` NPCs on the adversarial opponent fallback (collision fix); seated friendly allies in the generic actor branch (kept out of `npcs_present` so the no-opponent guard is unaffected — ADR-116 invariant preserved); tagged `participant.joined` `source="friendly_fallback"` for friendly seats; guarded `_roll_and_persist_initiative` against NPC allies without masking real PC name-skew.
- `tests/server/dispatch/test_59_35_friendly_companion_seating.py` — removed an unused import + ruff format (TEA-authored test content unchanged).

**Approach:** Reuse-first per the Architect (White Queen). No new data model — the ally is armed by its existing `Npc.core` HP (ADR-114). Combat-category only; sealed-letter (1v1) and table_resolution paths untouched (they branch earlier).

**Acceptance criteria:**
- AC1 (symmetric seater) — `test_present_friendly_npc_seated_as_player_side` + 3 boundary guards (hostile/neutral/absent) + the collision guard `test_friendly_ally_not_conscripted_as_opponent_when_room_sourced`. ✅
- AC2 (armed via existing channels) — `test_friendly_ally_armed_with_real_stat_block_in_hp_depletion_combat` (real `space_opera` hp_depletion; ally keeps its own 7/12 pool + resolvable AC). ✅
- AC3 (no-opponent invariant preserved) — friendly allies kept OUT of `npcs_present`; the existing `tests/server/test_chase_opponent_seating.py::test_chase_with_empty_room_raises_no_opponent` still passes. ✅
- AC4 (OTEL lie-detector) — `test_friendly_seat_emits_participant_joined_span` asserts `source="friendly_fallback"`, `side="player"`. ✅
- AC5 (Guitar Solo frame delivery) — `test_friendly_ally_appears_in_confrontation_payload_actors` (ally reaches the CONFRONTATION payload roster). ✅

**Tests:** 8/8 story tests passing (GREEN, RUN_ID `59-35-dev-green`). No regressions: 292 passing across the encounter/confrontation/dispatch/SWN suites. The full-suite run shows 9–10 pre-existing failures in UNRELATED subsystems (clue-discovery wiring, world-patch stakes, yield multi-PC, retrieval orchestration, output compaction, enum count) — **verified pre-existing** by stashing my source change and reproducing the identical 9-failed/1-passed in isolation (the 9-vs-10 delta is a pytest-xdist ordering flake, not my change).
**Branch:** `feat/59-35-seat-friendly-companions-player-combatants` (pushed)

**Handoff:** To Architect (spec-check), then Reviewer.

## Subagent Results (Round 1 — REJECTED)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (1 trivial conditional skip, not a defect) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings (assessed by Reviewer directly) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings (assessed by Reviewer directly) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 4 (1 HIGH, 3 LOW), downgraded 1 to LOW, dismissed 1 |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 3 (LOW) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings (assessed by Reviewer directly) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings (N/A — internal engine, no auth/input/tenant surface) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings (assessed by Reviewer directly) |
| 9 | reviewer-rule-checker | Yes | findings | 2 | confirmed 1 (LOW), dismissed 1 (borderline) |

**All received:** Yes (4 enabled returned; 5 disabled pre-filled as Skipped and their domains assessed by the Reviewer directly)
**Total findings:** 2 HIGH (1 from test-analyzer + 1 Reviewer-confirmed AC gap), 7 LOW confirmed, 2 dismissed (with rationale)

## Reviewer Assessment (Round 1 — REJECTED)

**Verdict:** REJECTED

Two acceptance-criteria gaps block approval: AC4's `participant.joined` span omits a required attribute, and AC3's load-bearing ADR-116 invariant has no test. The implementation's *seating* behavior is correct and well-built (verified end-to-end), but an incomplete AC and an untested invariant cannot ship.

### Severity Table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [TEST] | **AC4 incomplete:** the friendly `participant.joined` span emits `last_seen_turn` (via `_stamp_attrs`) but NOT `disposition_attitude`, which story AC4 explicitly requires ("source='friendly_fallback', side='player' (+ disposition_attitude, last_seen_turn)"). Implementation gap + untested. | `encounter_lifecycle.py:1182-1197` (span emit); `test_..._participant_joined_span` | Add `disposition_attitude` to the friendly seat's span attrs; assert it (and `last_seen_turn`) in the OTEL test. |
| [HIGH] [TEST] | **AC3 untested:** no test asserts that PC + present FRIENDLY ally + zero opponents still raises `NoOpponentAvailableError`. The story lists AC3 as a named vector; TEA's claim that the existing `test_chase_opponent_seating::test_chase_with_empty_room_raises_no_opponent` covers it is wrong — that test has NO ally present, so it cannot prove a friendly ally fails to satisfy the guard. A regression seating the ally as the Other would pass all 8 tests undetected. (Implementation IS correct — verified the friendly-skip + keep-out-of-`npcs_present` makes the guard fire — but the invariant is unguarded by tests.) | new test in `test_59_35_friendly_companion_seating.py` | Add `pytest.raises(NoOpponentAvailableError)` with `npcs_present=[]` + only a FRIENDLY NPC in `snapshot.npcs`. |
| [LOW] [TEST] | `test_absent_friendly_npc_not_seated` + `test_neutral_npc_not_seated_as_player` pass against a no-op seater (evidence of absence, not of the discriminator). | test file:218, 236 | Pair each with a FRIENDLY-at-`_LOC` control in the same body so location/disposition is the proven discriminator. |
| [LOW] [TEST] | `assert mara_npc.core.armor_class >= 1` is vacuous — AC defaults to 10 and the seeder skips player-side, so it can't fail. | test file:~470 | Assert `== 10` (proves the player-side block is NOT clobbered by `_seed_combat_hp_depletion_to_npcs`). |
| [LOW] [TEST] | `'Raider' not in _player_side_names(enc)` is entailed by the preceding `raider.side == 'opponent'` — tautological. | test file:~213 | Drop the redundant assertion (or replace with an independent check). |
| [LOW] [DOC] | `_npc_fallback_at_location` docstring still claims it "pulls in every location NPC as an opponent … byte-identical when adversary_only=False" — false since the FRIENDLY-skip was added. | `encounter_lifecycle.py:~505-514` | Update the Story 59-17 paragraph to note FRIENDLY exclusion (59-35). |
| [LOW] [DOC] | Test module docstring "RED tests. These FAIL today" is stale — this PR is the implementation; tests are green. | test file:1-5 | Reword to past tense. |
| [LOW] [DOC] | Test docstring says the seater runs "AFTER the opponent fallback and BEFORE the no-opponent guard" — it actually runs AFTER the guard. Misdirects maintainers. | test file:14-18 | Correct the placement description (see Reviewer deviation audit). |
| [LOW] [RULE]/[TYPE] | `_friendly_fallback_at_location` returns bare `list` (and `friendly_allies: list`) where `.name` is accessed on elements — `list[NpcMention]` would let mypy catch a wrong-element regression. | `encounter_lifecycle.py:561, ~1049` | Annotate `list[NpcMention]`. |

### Dispatch tags (all 8 represented)
- **[EDGE]** (self-assessed, subagent disabled): traced the explicit-opponent + co-located-friendly, empty-`npcs_present` collision, name-collision, and multi-ally paths — dedup + FRIENDLY-skip handle them; no unhandled boundary. The only edge nit is the LOW initiative name-collision (a PC whose name equals an NPC's and is missing from `characters` would be silently skipped) — pathological, noted not blocking.
- **[SILENT]** (self-assessed + [RULE] corroborated): the `_roll_and_persist_initiative` `continue` is NOT a silent fallback — gated on roster membership, documented, preserves the PC-skew raise. Confirmed by rule-checker.
- **[TEST]** the two HIGH gaps + 3 LOW test-quality items above (test-analyzer).
- **[DOC]** 3 stale comments (comment-analyzer), all confirmed.
- **[TYPE]** (self-assessed + [RULE]): bare `list` annotation; otherwise types sound (`side` validated via `_validate_side`).
- **[SEC]** (disabled, self-assessed): N/A — internal engine path, reads `snapshot.npcs` (server state), no user input / auth / tenant surface introduced.
- **[SIMPLE]** (self-assessed): the `_join_source` if/elif/else and the dedup set are minimal and clear; no over-engineering or dead code.
- **[RULE]** bare-`list` annotation (LOW); all 17 checked rules incl. No-Silent-Fallbacks, OTEL, wiring-test, no-source-text-test → compliant.

### Rule Compliance (lang-review python.md, enumerated against the diff)
- #1 silent exceptions — compliant (no new except/suppress; the `continue` is a loop guard, not exception handling).
- #2 mutable defaults — compliant (`acting_character_name: str | None = None`, `adversary_only: bool = False`).
- #3 type annotations — **1 LOW**: bare `list` on the new helper (private → rule-exempt, but flagged for precision since `.name` is accessed).
- #4 logging — compliant (no error paths added; observability via OTEL spans per project pattern).
- #5 path handling — compliant (no path ops; test uses `pathlib`).
- #6 test quality — **findings**: 2 vacuous negatives, 1 vacuous AC assertion, 1 tautology (all LOW); `assert ally_entries` dismissed (it's the filtered-by-name list, semantically specific, and the next line checks `.side`).
- #7 resource leaks — compliant (otel_capture fixture uses try/finally shutdown).
- #8 unsafe deserialization — compliant (none).
- #9 async — compliant (all sync).
- #10 import hygiene — compliant (the deferred `NpcMention` import mirrors the sibling's circular-import-avoidance pattern; runtime use, correct).
- #11 input validation — compliant (reads server-internal `snapshot.npcs`).
- #12 dependency hygiene — compliant (no dep changes).
- #13 fix-regressions — the only fix-introduced gap is the bare-`list` annotation (LOW).

### Devil's Advocate
Argue the code is broken. **First attack — the invariant.** The whole point of ADR-116 is "a confrontation requires an Other." This story adds the first non-PC `side="player"` actor. What stops a future refactor from counting that ally toward the Other requirement? Nothing in the test suite. AC3 is the guard rail and it is missing — I confirmed `grep` returns zero `NoOpponentAvailableError` tests in the new file. Today the code is correct (allies are kept out of `npcs_present`, so the guard fires on the empty list before seating), but that correctness rests entirely on an undocumented ordering choice (the seater runs after the guard) and the keep-out-of-`npcs_present` discipline. A maintainer who "tidies" the seater to append allies into `npcs_present` (a natural-looking simplification) would silently break the invariant and every test would stay green. That is the exact Illusionism failure mode SOUL warns about — convincing green with no mechanical guard. **Second attack — the lie detector.** AC4 demands `disposition_attitude` on the span precisely so the GM panel can prove the engine seated the ally *because it read FRIENDLY disposition*, not because the narrator invented an ally. The implementation omits it. So the one OTEL attribute that proves *why* the ally was seated is absent — the lie detector is half-blind on exactly the new decision this story introduces. **Third attack — the vacuous tests.** A confused future dev reading `test_absent_friendly_npc_not_seated` and `test_neutral_npc_not_seated_as_player` would believe disposition/location filtering is verified. It is not — both pass against a deleted `_friendly_fallback_at_location`. Combined with the `armor_class >= 1` floor that can never fail, three of the eight tests are weaker than they read. The seating feature itself is genuinely well-built — but "looks tested" is not "is tested," and on a load-bearing engine invariant that gap is the finding.

### Observations (≥5)
1. [VERIFIED] ADR-116 invariant correctly implemented — `_friendly_fallback_at_location` results are kept out of `npcs_present`; the no-opponent guard at `encounter_lifecycle.py:~1020` is unaffected. Evidence: friendly_allies computed at :1043 (after the guard), seated only in the generic branch at :1147.
2. [VERIFIED] OTEL `source="friendly_fallback"` wired — `encounter_lifecycle.py:1187`; distinct from PC `seat` and opponent `seating_source`. (But missing `disposition_attitude` — see HIGH.)
3. [HIGH][TEST] AC3 invariant untested (confirmed by grep).
4. [HIGH][TEST] AC4 span attribute `disposition_attitude` missing from impl + test.
5. [LOW][DOC] 3 stale comments (comment-analyzer, confirmed).
6. [LOW][TEST] 2 vacuous negatives + 1 vacuous AC floor + 1 tautology.
7. [LOW][TYPE] bare `list` annotation on the new helper.
8. [VERIFIED] No regressions — preflight GREEN on the 8 story tests; the 9–10 full-suite failures are pre-existing, unrelated (Dev verified by stash-and-reproduce).

**Handoff:** Back to TEA (red rework) — the dominant work is test-side (add the AC3 raise-test, assert `disposition_attitude`+`last_seen_turn`, harden the vacuous assertions, fix the stale test docstrings). The `disposition_attitude` span emit, the source docstring, and the `list[NpcMention]` annotation are then completed by Dev in the following green pass driven by the new failing assertion.

## Subagent Results

(Re-review after rework round-trip 1 — same 4 enabled subagents re-run on the full updated diff.)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (9/9 green, lint clean, 1 legit skip) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings (assessed by Reviewer directly) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings (assessed by Reviewer directly) |
| 4 | reviewer-test-analyzer | Yes | findings | 2 | confirmed 2 (1 LOW dead-code, 1 MEDIUM neutral full-absence) |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 | confirmed 6 (LOW stale/misleading docstrings) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings (assessed by Reviewer directly) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings (N/A — internal engine) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings (assessed by Reviewer directly) |
| 9 | reviewer-rule-checker | Yes | clean | 0 violations (17 rules × 61 instances) | N/A |

**All received:** Yes (4 enabled returned; 5 disabled pre-filled as Skipped and assessed by the Reviewer directly)
**Total findings:** 0 HIGH (both round-1 HIGH blockers RESOLVED + verified), 7 LOW + 1 MEDIUM confirmed (all non-blocking)

## Reviewer Assessment

**Verdict:** APPROVED

Both round-1 HIGH blockers are **resolved and independently verified**: AC4's `participant.joined` span now carries `disposition_attitude` (friendly seats read `'friendly'`), and AC3's ADR-116 invariant is now guarded by `test_friendly_ally_alone_still_raises_no_opponent`. The re-review's rule-checker came back **CLEAN (0 violations across 17 rules)**, preflight is **GREEN (9/9)**, and the prior vacuous assertions / stale docstrings / bare-`list` annotation were fixed. Remaining findings are all LOW/MEDIUM and below the blocking threshold (Critical/High only) — recorded as non-blocking.

**Data flow traced:** a FRIENDLY `snapshot.npcs` entry at the acting PC's location → `_friendly_fallback_at_location` (`side="player"`, kept OUT of `npcs_present`) → seated in the generic actor branch → `participant.joined` span (`source="friendly_fallback"`, `disposition_attitude="friendly"`) → `build_confrontation_payload` actors roster (verified by the AC5 wiring test). Safe: the no-opponent guard runs before ally sourcing, so the ADR-116 invariant holds (AC3 test pins it).

**Pattern observed:** reuse-first symmetric helper mirroring `_npc_fallback_at_location`; OTEL-on-every-decision honored (`encounter_lifecycle.py` span loop).

**Error handling:** `_roll_and_persist_initiative` NPC-ally skip is gated on roster membership and preserves the fail-loud raise for genuine PC name-skew (rule-checker confirmed: not a silent fallback).

### Round-1 blocker resolution (verified)
- **AC4 (was HIGH):** `disposition_attitude` now emitted for all roster-NPC seats (`encounter_lifecycle.py:1192`, `.attitude().value`); `test_friendly_seat_emits_participant_joined_span` asserts `== "friendly"` + `last_seen_turn == 2` and passes. ✓
- **AC3 (was HIGH):** `test_friendly_ally_alone_still_raises_no_opponent` added — `pytest.raises(NoOpponentAvailableError)` for PC + FRIENDLY ally + zero opponents. The primary assertion guards the invariant. ✓
- LOW round-1 items all fixed: paired-control negatives, `armor_class == 10`, tautology replaced, 3 docstrings corrected, `list[NpcMention]` annotation.

### Non-blocking findings (LOW/MEDIUM — recommend fast-follow cleanup)
| Severity | Issue | Location | Suggested fix |
|----------|-------|----------|---------------|
| [MEDIUM] [TEST] | `test_neutral_npc_not_seated_as_player` asserts only `"Bystander" not in _player_side_names` — a neutral seated `side="neutral"`/`"opponent"` would still pass. The story wants neutral NOT seated at all. | test file | Add `assert _actor(enc, "Bystander") is None`. (Today it IS absent — npcs_present non-empty skips the opponent fallback — so this is a strengthening, not a live bug.) |
| [LOW] [TEST] | AC3 test's secondary `if snap.encounter is not None: assert opp` block is DEAD CODE — the raise (line 1042) precedes `snapshot.encounter = enc` (1304), so `snap.encounter` is always None on this path. The primary `pytest.raises` already guards the invariant. | test file `test_friendly_ally_alone_still_raises_no_opponent` | Replace with unconditional `assert snap.encounter is None` (a real post-raise invariant). |
| [LOW] [DOC] | 4 per-test docstrings still use pre-implementation present tense ("Today the seating loop … is never seated", "currently conscripts EVERY …", "Today every side='player' span hardcodes source='seat'", "today the ally is never seated"). The rework past-tensed the module docstring + 3 others but left these — a half-finished cleanup. | test file (test_present_friendly, test_collision, test_AC4_span, test_AC5_payload docstrings) + the Background "MISSING half / This is the FIRST" present tense | Past-tense them to match. |
| [LOW] [DOC] | The `disposition_attitude` comment (`encounter_lifecycle.py:~1188-1191`) frames the attr as friendly-seat-exclusive; it's actually emitted for ALL roster-NPC seats (opponents read `hostile`/`neutral`). | `encounter_lifecycle.py` | Broaden the comment to "every roster-NPC seat carries its disposition band". |

### Dispatch tags (all 8 represented)
- **[EDGE]** (self-assessed, disabled): re-traced the rework delta — `disposition_attitude` for all roster seats, the AC3 raise path, paired-control negatives. The only edge nit is the AC3 dead-code block (LOW, below). No unhandled boundary.
- **[SILENT]** (self + [RULE]): rule-checker re-confirmed the initiative `continue` and the `_friendly_fallback` empty-location return are documented non-fallbacks. ✓
- **[TEST]** test-analyzer: 1 LOW dead-code, 1 MEDIUM neutral full-absence (both non-blocking; primary AC3 guard + neutral player-side check both work).
- **[DOC]** comment-analyzer: 6 LOW stale/misleading docstrings (the rework's half-finished past-tensing + the disposition_attitude comment scope).
- **[TYPE]** (self + [RULE]): bare-`list` finding RESOLVED → `list[NpcMention]`; rule-checker confirmed clean.
- **[SEC]** (disabled, self-assessed): N/A — internal engine, no auth/input/tenant surface.
- **[SIMPLE]** (self-assessed): the disposition_attitude addition is one dict key; no over-engineering. The one dead-code block (AC3 test) is flagged under [TEST].
- **[RULE]** rule-checker: CLEAN, 0 violations across 17 rules (incl. No-Silent-Fallbacks, OTEL, wiring-test, no-source-text-test, annotation precision).

### Devil's Advocate
Can I still break it? **The invariant:** the round-1 fear (a refactor appending allies into `npcs_present`) is now guarded by `test_friendly_ally_alone_still_raises_no_opponent` — its `pytest.raises` fails if the ally ever satisfies the guard. The dead secondary block doesn't add coverage, but the primary assertion is load-bearing and works, so the invariant IS protected. **The lie detector:** AC4's `disposition_attitude` is now emitted and asserted — the GM panel can prove the seat was disposition-driven. **The tests:** the negatives now carry FRIENDLY controls, so they fail against a no-op seater; `armor_class == 10` can now catch a clobber; the tautology is gone. The residual weaknesses (neutral full-absence not asserted; 4 stale docstrings; one dead assertion) are real but LOW/MEDIUM — none lets broken behavior pass undetected. The strongest remaining critique is the half-finished docstring cleanup (a craft/consistency issue), not a correctness one. Below the blocking bar.

### Observations (≥5)
1. [VERIFIED] AC4 resolved — `disposition_attitude="friendly"` emitted + asserted (`encounter_lifecycle.py:1192`; test passes).
2. [VERIFIED] AC3 resolved — invariant test added; primary `pytest.raises` guards it (raise at :1042 precedes encounter assignment at :1304, verified).
3. [VERIFIED] rule-checker CLEAN — 0 violations across 17 rules; bare-`list` annotation fixed to `list[NpcMention]`.
4. [VERIFIED] No regressions — 9/9 story green, 293 passing across encounter/confrontation/SWN/participant suites; pyright == develop baseline (0 introduced).
5. [MEDIUM][TEST] neutral test asserts player-side absence only, not full absence (strengthening, not a live bug).
6. [LOW][TEST] AC3 dead-code secondary block (primary guard works).
7. [LOW][DOC] 4+ per-test docstrings + Background still pre-implementation present tense (half-finished cleanup); disposition_attitude comment over-scopes.
8. [VERIFIED] OTEL discipline upheld — the new seating decision and its disposition rationale are both observable on `participant.joined`.

**Handoff:** To SM for finish-story. The LOW/MEDIUM findings are recorded as non-blocking delivery findings — recommend a fast-follow `/chore` (test docstring past-tensing + AC3 dead-code → `assert snap.encounter is None` + neutral full-absence assertion + broaden the disposition_attitude comment); none warrants a third TDD round-trip.

## Technical Context

### Story Goal

Enable allied NPCs to fight on side=player in confrontations (completing ADR-116's friendly side of seating + enacting the SOUL Guitar Solo principle: "others get a concurrent meaningful part, never a silent audience"). This is the first non-PC actor seated on side=player.

### Architecture Overview

**Key Components:**
1. **instantiate_encounter_from_trigger** (encounter_lifecycle.py:724) — the central encounter-seating orchestrator
   - Currently seats opponents via `_npc_fallback_at_location` (~464-537)
   - Currently seats PCs via implicit seating (1040-1047)
   - Needs: symmetric `_friendly_fallback_at_location` for friendly NPCs

2. **EncounterActor** (game/encounter.py:105-127) — already accepts `side='player'`

3. **Disposition + Attitude** (game/disposition.py:95-189) — Attitude.FRIENDLY exists

4. **NPC Scene Presence** (game/npc_scene.py:99-150) — `is_npc_in_scene(npc, encounter, current_room)` predicate

5. **Combat HP Seeding** — reuse existing `_seed_combat_hp_depletion_to_npcs` / `_publish_combat_edge_to_npcs` (ADR-114 ablative HP already in Npc.core)

6. **Per-Recipient Frame Delivery** (server/dispatch/confrontation.py) — `make_confrontation_frame_supplier` is seat-agnostic; allied NPCs automatically get filtered beats

7. **OTEL Watcher** (telemetry/spans/encounter.py:105-115) — `participant.joined` span already carries `source` attr

### Acceptance Criteria Summary

1. **Symmetric friendly-seater** — Add `_friendly_fallback_at_location` parallel to opponent fallback; invoke after opponent seating (~925) and before no-opponent guard (946). Seats scene-present, FRIENDLY-disposition, not-withdrawn NPCs as `EncounterActor(side='player')`. Test all three paths: present friendly (seated), present hostile (not seated), absent friendly (not seated).

2. **Armed via existing channels** — Friendly-seated NPCs get real stat blocks through the same `_seed_combat_hp_depletion_to_npcs` / `_publish_combat_edge_to_npcs` paths used for opponents. No new data model. Test: friendly-seated NPC in hp_depletion confrontation has seeded core.hp/armor_class.

3. **Invariant preserved** — Friendly seating does NOT satisfy "confrontation requires an Other" (still gates on side=opponent). PC + friendly ally with zero opponents still hits no-opponent path (NoOpponentAvailableError / graceful prose), unchanged. Test: zero-opponent case still works.

4. **OTEL lie-detector** — Each friendly seat emits `participant.joined` with `source='friendly_fallback'`, `side='player'`, plus `disposition_attitude` and `last_seen_turn`. Test: span asserted per friendly seat via real OTEL span capture (not source grep).

5. **Guitar Solo delivery (wiring)** — Seated ally appears in per-recipient CONFRONTATION frame (actors roster) via existing `make_confrontation_frame_supplier`. No silent audience. Test: begin confrontation with present friendly NPC, assert emitted CONFRONTATION payload includes ally with side='player'.

6. **Explicit non-goals:**
   - Roster-only Companions (no stat block) not seated as combatants
   - Social/audience-trial friendly seating (ADR-116 §3, deferred)
   - Ally-seating balance tuning (ADR-093)

### Key Design Decisions

- **Friendly = disposition.attitude() == Attitude.FRIENDLY AND scene-present AND not withdrawn**
  - Hostile/neutral NPCs are NOT auto-seated to player
  - Hostile/neutral remain seated on opponent fallback only (existing behavior)

- **Scene-present determination:** `is_npc_in_scene(npc, encounter, current_room)` and `last_seen_location == acting actor's party_location`

- **No new data model** — reuse existing Npc.core HpPool + armor_class (ADR-114)

- **Seating order in instantiate_encounter_from_trigger:**
  1. Opponent fallback (_npc_fallback_at_location, existing)
  2. Friendly fallback (_friendly_fallback_at_location, new) ← INSERT HERE
  3. No-opponent guard (existing, still gates on side=opponent)

- **OTEL source attribution:** Reuse `participant.joined` span's `source` attribute; set to `'friendly_fallback'` for friendly NPCs, distinguishing from router-named/location-fallback/player threats

### Testing Strategy

**Unit Tests:**
- `_friendly_fallback_at_location` isolated: friendly present → seated, hostile present → not seated, absent → not seated
- HP seeding parity: friendly-seated NPC gets same stat block as opponent-seated NPC

**Wiring Tests (per CLAUDE.md):**
- End-to-end confrontation fixture with present friendly NPC
  - Assert friendly NPC appears in encounter.actors with side='player'
  - Assert participant.joined span emitted with source='friendly_fallback'
  - Assert CONFRONTATION payload to players includes ally actor with side='player' in actors roster

**Regression Tests:**
- No-opponent case (PC + friendly ally, zero opponents) still raises NoOpponentAvailableError
- Existing opponent fallback behavior unchanged (hostile/neutral still seated as side=opponent)

### ADR References

- **ADR-116 (A Confrontation Requires an Other)** — friendly seating completes the symmetry; no-opponent invariant unchanged
- **ADR-114 (Ablative HP Substrate)** — reuse existing Npc.core HP seeding
- **CLAUDE.md (SOUL Principles)** — Guitar Solo principle ("others get a concurrent meaningful part, never a silent audience")

---

**Branch:** feat/59-35-seat-friendly-companions-player-combatants
**Repo:** sidequest-server