---
story_id: "90-6"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 90-6: Region-mode location-drift abandons live combat the turn it instantiates

## Story Details
- **ID:** 90-6
- **Jira Key:** (not in use)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-09T11:40:58Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-06T00:00:00Z | 2026-06-07T03:55:36Z | 27h 55m |
| red | 2026-06-07T03:55:36Z | 2026-06-07T06:12:25Z | 2h 16m |
| green | 2026-06-07T06:12:25Z | 2026-06-09T11:13:50Z | 53h 1m |
| review | 2026-06-09T11:13:50Z | 2026-06-09T11:22:00Z | 8m 10s |
| red | 2026-06-09T11:22:00Z | 2026-06-09T11:29:47Z | 7m 47s |
| green | 2026-06-09T11:29:47Z | 2026-06-09T11:33:32Z | 3m 45s |
| review | 2026-06-09T11:33:32Z | 2026-06-09T11:40:58Z | 7m 26s |
| finish | 2026-06-09T11:40:58Z | - | - |

## Sm Assessment

Root cause is already measured and pinned to a single fix lane — `sidequest-server/sidequest/server/narration_apply.py`. The encounter-abandon block (~L3298 `if old_loc != result.location`) keys off the raw location STRING, so in region-mode worlds the narrator's per-turn cosmetic scene re-title (`narrator.location_drift_repaired` fires every turn) reads as a location change and abandons the just-instantiated combat at L3451→L3455 (`encounter.deactivated_on_location_change`, outcome `abandoned_on_location_change`). The signal to fix this already exists: L3218–3244 detects `region.entry_skipped_sub_location` (same-region sub-location POI) but the abandon block ignores it.

**Scope discipline:** server-only, one file. Not #707 (that's space_opera Firefight, a different resolution mode). Not the ADR-113 confidence gate (per-dispatch gating isn't operational). Distinct from 90-3 but BLOCKS it for every region-mode ruleset world (perseus/swn, the_circuit/cwn) — so this lands first.

**OTEL is load-bearing here.** Per project doctrine, the GM panel is the lie detector: the failure mode is the narrator free-handing hit/miss with `confrontation=None active=False` forever. TEA must assert a watcher/OTEL span proves the confrontation *continued* across a same-region drift, not just that the code path was taken. AC2 already calls for this — make it a hard assertion, not a soft check.

**Regression guard required:** a REAL region change MUST still abandon an anchored confrontation, and mobile confrontations must keep existing continue behavior (AC3/AC4). The fix narrows the abandon trigger; it must not disable it.

Workflow: tdd (phased). Routing to TEA (Amos) for RED. Branch and context are in place.

## TEA Assessment

**Tests Required:** Yes
**Reason:** P1 behavioral bug with five measurable ACs in one fix lane (`narration_apply.py`).

**Test Files:**
- `tests/server/test_region_mode_drift_keeps_combat.py` — 11 tests pinning the five ACs + a region-mode gating guard + a dispatch-branch wiring test.

**Tests Written:** 11 tests covering 5 ACs.
**Status:** RED (5 failing as designed; 5 regression/gating guards + sibling suite green).

Verified directly (`pytest -n0`): **5 failed, 5 passed** in the new file; the sibling `test_confrontation_location_change.py` suite stays **12 passed** (fix must not regress non-region-mode behavior).

| AC | Test(s) | RED status |
|----|---------|------------|
| AC1 no-abandon | `test_same_region_scene_drift_does_not_abandon_combat` | **failing** (combat wrongly abandoned) |
| AC1 OTEL | `test_same_region_drift_does_not_emit_deactivation_span` | **failing** (deactivation span fires) |
| AC2 continue span | `test_same_region_drift_emits_confrontation_continued_span` | **failing** (no continue span) |
| AC3 real change abandons | `test_real_region_change_still_abandons_anchored_combat` | passing (guard — current behavior correct) |
| AC3 OTEL | `test_real_region_change_emits_deactivation_span` | passing (guard) |
| AC4 mobile same-region | `test_mobile_chase_continues_on_same_region_drift_in_region_mode` | passing (guard) |
| AC4 mobile real-change | `test_mobile_chase_continues_on_real_region_change_in_region_mode` | passing (guard) |
| AC5 survival proxy | `test_combat_survives_multiple_same_region_drifts` | **failing** (dies on first drift) |
| gating | `test_non_region_mode_world_still_abandons_combat_on_location_change` | passing (guard — fix must stay scoped) |
| wiring | `test_same_region_continue_keeps_dispatch_branch_from_clearing_panel` | **failing** (now_live=False, panel torn down) |

### Rule Coverage (lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality — meaningful, non-vacuous assertions | every test asserts encounter `resolved`/`outcome` or watcher `event_type` | enforced |
| OTEL principle — subsystem decision must emit a span | `test_same_region_drift_emits_confrontation_continued_span` (continue), `test_real_region_change_emits_deactivation_span` (abandon) | failing/passing |
| No source-text wiring tests | wiring test asserts runtime boolean arithmetic (`prior_live`/`now_live`), not source greps | enforced |

**Rules checked:** test-quality, OTEL-emission, and no-source-text-wiring are the applicable lang-review rules for a single-function behavioral fix. **Self-check:** 0 vacuous tests — every test has a state or event assertion with a failure message.

**Dev guidance:** narrow the abandon trigger at `narration_apply.py` ~L3470 (`else`) so a region-mode same-region sub-location drift CONTINUES the anchored confrontation and emits a `confrontation_continued_*` watcher event (component="confrontation", with `encounter_type`); only a REAL cartography-region change (the `known_region_id` path that advanced `current_region`) still abandons. Reuse the `_resolve_heading_to_cartography`/`known_region_id` result already computed upstream rather than re-deriving (see Delivery Finding). Do NOT touch the mobile-continue or non-region-mode paths — guards lock both.

**Handoff:** To Dev (Naomi) for GREEN.

---

### Red Phase — Rework Round 2 (2026-06-09, post-REJECT)

Reviewer (Chrisjen) REJECTED the GREEN: the same-region-continue branch
(`narration_apply.py` ~L3487) is not scoped to combat — it continues ANY
non-mobile category, so a region-mode SOCIAL negotiation walked out of within a
region stays live (reintroduces the 2026-04-30 negotiation-walk-out / puppet-NPC
bug). Returned to TEA because the blocking fix needs new category-scoping tests.

**Tests Added/Changed:** 3 new RED + 1 wiring-test repair (same file).

| Finding | Test | RED status |
|---------|------|------------|
| [HIGH][EDGE][RULE] continue not combat-scoped | `test_same_region_drift_abandons_social_negotiation_in_region_mode` | **failing** (social wrongly continued) |
| [HIGH] OTEL companion | `test_same_region_drift_social_emits_deactivation_not_continue_span` | **failing** (continue span fires for social) |
| [MEDIUM][SILENT][EDGE] invalid heading abandons combat | `test_invalid_heading_does_not_abandon_combat_in_region_mode` | **failing** (garbage title abandons combat) |
| [MEDIUM][TEST] tautological wiring test | `test_same_region_continue_does_not_emit_panel_clear_signal` (renamed/rewritten) | passing (green guard — now asserts real OTEL signal) |

**Verified directly (`pytest -n0`):** new file **3 failed, 10 passed**; sibling
`test_confrontation_location_change.py` stays **12 passed**. `ruff check` +
`ruff format --check` clean.

**Wiring-test repair:** dropped the tautological `assert not (prior_live and not
now_live)` (it reduced to `assert not False`). The repaired test asserts the
refactor-stable OTEL signature the dispatch branch keys on — `confrontation_
deactivated_on_location_change` ABSENT (it co-fires with the resolved-flip that
builds the `CONFRONTATION{active:false}` clear payload) AND a `confrontation_
continued_*` span PRESENT — per server CLAUDE.md "No Source-Text Wiring Tests".

### Rule Coverage (rework)

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test quality — non-vacuous, real signal | wiring test now asserts watcher spans, not self-derived booleans; tautology removed | enforced |
| #13 fix-introduced regression (combat scope) | `test_same_region_drift_abandons_social_negotiation_in_region_mode` pins social keeps abandoning | failing (RED) |
| OTEL principle — subsystem decision emits a span | social-abandon asserts deactivation span; invalid-heading asserts no spurious deactivation | failing (RED) |
| No source-text wiring tests | repaired wiring test uses OTEL-span assertions (sanctioned pattern) | enforced |

**Self-check:** 0 vacuous tests remain — the one tautological assertion the
Reviewer flagged is removed; every test asserts encounter state and/or watcher
`event_type` with a failure message.

**Dev guidance (GREEN round 2):**
1. Gate the same-region-continue `elif` (~L3487) on combat: add `getattr(active_encounter, "category", "") == "combat"` to its condition so social/other anchored categories fall through to the existing abandon branch.
2. Hoist the `_is_region_mode_world` / `_region_mode_world_active` computation ABOVE the `if not is_valid_region:` gate (~L3110). It reads only `pack.worlds[world].cartography.navigation_mode`, never the location string — safe to compute before validation — so a region-mode combat survives a garbage re-title (current_region cannot have advanced on a rejected heading). Keep the valid-region branch's existing use intact.
Do NOT touch the mobile-continue path or the non-region-mode abandon path — guards lock both.

**Handoff:** To Dev (Naomi) for GREEN round 2.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): AC5's full live proof (Perseus SWN combat with `beat_selections>0` and an `hp_depletion`/strike damage patch on tracked enemy HP) is not unit-testable here — it needs a live narrator + intent-router turn. It is covered by a deterministic two-turn survival PROXY (`test_combat_survives_multiple_same_region_drifts`) and must be re-run by the playtest DRIVER post-merge (`~/Projects/sq-playtest-pingpong.md`). Affects the Perseus repro path (no code change required) — Dev/Reviewer should not consider AC5 fully closed until the DRIVER re-run lands. *Found by TEA during test design.*
- **Improvement** (non-blocking): the abandon block (`narration_apply.py` ~L3470 `else`) and the upstream region-resolution block (~L3142-3292) both independently need to know "did this location change cross a cartography region boundary?" The signal is computed once at the top (`_resolve_heading_to_cartography` → `known_region_id`); Dev should thread/reuse that result into the abandon decision rather than recomputing, to keep the two in lockstep. Affects `sidequest/server/narration_apply.py` (single resolution, two consumers). *Found by TEA during test design.*
- **Improvement** (non-blocking): the same-region continue branch is gated combat-only (per Reviewer finding 1). Anchored non-combat categories other than `social` (e.g. a future `hacking` confrontation) will therefore abandon on a same-region drift — re-hitting the instantiate-then-die loop for that category. None ship today (only movement/social/combat categories exist on shipping packs), so this is a known boundary of the combat-scoped fix, not a defect. Affects `sidequest/server/narration_apply.py` (the combat gate on the continue branch) — revisit if a region-mode anchored non-combat-non-social confrontation surfaces in playtest. *Found by TEA during test design (RED rework).*

### Reviewer (code review)
- **Gap** (blocking): the same-region-continue `elif` is not scoped to combat — it continues ANY non-mobile (anchored) encounter, including `category="social"`. A region-mode social negotiation walked out of within the same region now stays live (beat buttons clickable, puppet narration) — the 2026-04-30 negotiation-walk-out bug, reintroduced for every region-mode world (oz/wonderland/gulliver/perseus/the_circuit). Affects `sidequest-server/sidequest/server/narration_apply.py` (~L3487 new `elif` — gate on combat category) and the test suite (no social-in-region-mode coverage). *Found by Reviewer during code review.*
- **Gap** (non-blocking): an invalid narrator heading (`validate_region_name` False — bracketed/multiline/too_long) in a region-mode world leaves `_region_mode_world_active=False`, so a live combat is abandoned on a garbage re-title (pre-existing behavior, but the fix could close it by computing region-mode before the validity gate). Affects `sidequest/server/narration_apply.py` (~L3151 assignment is inside the valid-region `else`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the wiring test re-derives the handler's `prior_live`/`now_live` booleans in its own body and its final assertion is tautological; it should assert the real signal the dispatch branch keys on (`confrontation_deactivated_on_location_change` absent from the watcher events). Affects `tests/server/test_region_mode_drift_keeps_combat.py` (~L572-616). *Found by Reviewer during code review.*
- **Improvement** (non-blocking, round 2): `test_invalid_heading_does_not_abandon_combat_in_region_mode` asserts combat-survives + deactivation-span-absent but not the positive `confrontation_continued_*` span. The continue branch's span emission is already pinned by the sibling AC2 test (same elif), and the deactivation-absent assertion falsifies the hoist-revert regression the test targets — so this is incremental hardening, not a correctness gap. Add `assert any(e.startswith(_CONTINUED_PREFIX) for e in _event_types(watcher_events))` next time the file is touched. Affects `tests/server/test_region_mode_drift_keeps_combat.py`. *Found by Reviewer during code review (round 2).*
- **Improvement** (non-blocking, round 2): the combat gate uses a literal `getattr(active_encounter, "category", "") == "combat"` with no pack-lookup fallback for legacy `category==""` encounters (unlike `_encounter_is_mobile`). Live region-mode worlds stamp `category` at instantiation so the repro path is unaffected, and there are no saves to migrate — but a defensive `_encounter_is_anchored_combat(enc, pack)` helper with the same fallback would be more symmetric. Affects `sidequest/server/narration_apply.py` (~L3492). *Found by Reviewer during code review (round 2).*

### Dev (implementation) — round 2
- No upstream findings during GREEN round 2. Implemented exactly to TEA's RED-rework tests and Dev guidance: combat-only gate on the continue branch + hoist the region-mode flag above the validity gate. TEA's round-2 boundary finding stands (anchored non-combat-non-social categories would abandon on a same-region drift; none ship today). No new gaps.

### Dev (implementation)
- No upstream findings during implementation. TEA's two findings stand: (1) AC5's full live proof (`beat_selections>0` + HP patch on tracked enemy HP) remains DRIVER-gated post-merge — the unit proxy `test_combat_survives_multiple_same_region_drifts` is green but Reviewer/SM should not treat AC5 as closed until the Perseus SWN DRIVER re-run lands; (2) the region-resolution signal was reused as recommended (no recompute) — `_region_mode_world_active` is set from the existing `_is_region_mode_world`, and the same-region determination keys off whether the upstream block advanced `current_region`.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/server/narration_apply.py` — narrowed the encounter-abandon trigger in `_apply_narration_result_to_snapshot`. (1) Captured `_region_before_location_update = snapshot.current_region` and a default-False `_region_mode_world_active` at the same seam as `old_loc`, BEFORE the region-resolution block can advance `current_region`. (2) Set `_region_mode_world_active = _is_region_mode_world` inside the valid-region branch, reusing the already-computed signal. (3) Added a new branch in the abandon block, placed AFTER the mobile-continue branch and BEFORE the `else` abandon: when `_region_mode_world_active and snapshot.current_region == _region_before_location_update` (region-mode world, no region crossing this turn), the anchored confrontation CONTINUES and emits a `confrontation_continued_same_region_drift` watcher span (component=`confrontation`, with `encounter_type`). A real region change advances `current_region` upstream, so it falls through to the existing abandon branch.

**Tests:** 22/22 passing (GREEN)
- `tests/server/test_region_mode_drift_keeps_combat.py`: 10/10 (5 previously-failing ACs now green, 5 guards stay green)
- `tests/server/test_confrontation_location_change.py`: 12/12 (sibling regression suite intact — mobile-continue, win/yield-on-leave, and non-region abandon all unchanged)
- `ruff check` + `ruff format --check`: clean

**Branch:** `feat/90-6-region-mode-location-drift-abandons-combat` (pushed)

**Handoff:** To Reviewer (Chrisjen) for review.

---

### Dev Assessment — GREEN Round 2 (2026-06-09, post-REJECT)

**Implementation Complete:** Yes — addresses all three Reviewer findings.

**Files Changed:**
- `sidequest-server/sidequest/server/narration_apply.py` — two changes in `_apply_narration_result_to_snapshot`:
  1. **[HIGH blocking]** Gated the same-region-continue branch (`~L3490`) on combat: added `and (getattr(active_encounter, "category", "") or "") == "combat"` to the `elif`. A social negotiation drifted within the same region now falls through to the existing abandon branch — the 2026-04-30 negotiation-walk-out / puppet-NPC semantics are preserved for every region-mode world. The continue no longer widens to all anchored categories.
  2. **[MEDIUM][SILENT]** Hoisted the `_is_region_mode_world` / `_region_mode_world_active` computation (incl. the `NavigationMode` import) ABOVE the `if not is_valid_region:` gate. It reads only `pack.worlds[world].cartography.navigation_mode` — never the narrator location string — so a garbage/rejected heading (`validate_region_name` False) is correctly a non-exit: `current_region` cannot have advanced, so a region-mode combat SURVIVES the bad re-title instead of being silently abandoned. Removed the now-duplicate in-`else` detection block; the valid-region branch's existing `_is_region_mode_world` uses are unchanged.
- The **[MEDIUM][TEST]** tautological wiring test was repaired by TEA in the RED rework (now asserts the real OTEL signature) — no Dev action needed beyond keeping it green.

**Tests:** GREEN.
- `tests/server/test_region_mode_drift_keeps_combat.py`: 13/13 (the 3 RED-rework tests now pass: social abandons + emits deactivation/no-continue; invalid heading keeps combat live)
- `tests/server/test_confrontation_location_change.py`: 12/12 (sibling regression intact)
- Regression sweep (14 adjacent region/narration-apply/confrontation suites, `-n0`): **128 passed, 5 skipped**
- `ruff check` + `ruff format`: clean

**Branch:** `feat/90-6-region-mode-location-drift-abandons-combat` (pushed — `a294fd3e`)

**Handoff:** To Reviewer (Chrisjen) for review round 2.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC5 live-proof implemented as a two-turn survival proxy**
  - Spec source: context-story-90-6.md, AC-5
  - Spec text: "the combat encounter survives across turns; beat_selections>0 and an hp_depletion/strike damage patch lands on tracked enemy HP (re-run by DRIVER post-merge)"
  - Implementation: `test_combat_survives_multiple_same_region_drifts` asserts the encounter stays `resolved=False` across two consecutive same-region drifts (the prerequisite for beats firing next turn). The `beat_selections>0` + HP-patch half is left to the DRIVER's post-merge Perseus re-run, as the AC itself specifies.
  - Rationale: beat selection / HP depletion requires a live narrator + intent-router turn against a real SWN pack; unit-driving it would be a fragile re-implementation of the dispatch pipeline. The AC explicitly delegates the live half to the DRIVER.
  - Severity: minor
  - Forward impact: Reviewer/SM must treat AC5 as DRIVER-gated, not closed at merge.
- **AC1/AC2 OTEL assertions target watcher events, not raw OTLP spans**
  - Spec source: context-story-90-6.md, AC-1 and AC-2
  - Spec text: "encounter.deactivated_on_location_change does NOT fire (OTEL span assertion)" / "emits a confrontation_continued_* watcher/OTEL span"
  - Implementation: the OTEL tests monkeypatch `narration_apply._watcher_publish` (the watcher-hub `publish_event` the GM panel reads) and assert on the captured `event_type`s, rather than installing an InMemorySpanExporter via `otel_capture`.
  - Rationale: these subsystem decisions emit via `_watcher_publish` (component="confrontation") — that IS the GM-panel lie-detector channel for this code path; capturing it synchronously needs no event loop and is refactor-stable. The continue span name is matched by prefix (`confrontation_continued`) so Dev may reuse the existing `_across_location_change` event or mint a same-region variant.
  - Severity: minor
  - Forward impact: none — Dev satisfies AC2 by emitting any `confrontation_continued_*` watcher event with `encounter_type` on the continue path.
- **RED rework (round 2): added an invalid-heading survival test beyond the strictly-blocking finding**
  - Spec source: Reviewer Assessment 2026-06-09 (REJECTED), finding 3 [MEDIUM][SILENT][EDGE]
  - Spec text: "Compute `_is_region_mode_world` / `_region_mode_world_active` BEFORE the `if not is_valid_region:` gate … Optional within this rework but recommended while the lane is open."
  - Implementation: added `test_invalid_heading_does_not_abandon_combat_in_region_mode` (RED) pinning combat-survives-garbage-title, which converts the Reviewer's *optional* recommendation into a *required* GREEN change for Dev.
  - Rationale: the invalid-heading abandon is a real silent failure in this exact code path (no causal span links a rejected heading to the lost encounter), it is cheap to close, the flag depends only on pack+world (safe to hoist above the gate), and project doctrine is "every playtest is production tomorrow — fix it right." Closing it while the lane is open is cheaper than a follow-up story.
  - Severity: minor
  - Forward impact: Dev MUST hoist the `_is_region_mode_world` / `_region_mode_world_active` computation above the `if not is_valid_region:` gate (it reads only `pack.worlds[world].cartography`, never the rejected location string). The combat-only gate from finding 1 still applies to the continue branch.
- **Combat-only continue scope pinned by example (combat continues / social abandons); other anchored categories not pinned**
  - Spec source: story title + SM Assessment (combat); Reviewer finding 1 ("Gate the elif on combat category")
  - Spec text: "Gate the `elif` on combat category (e.g. `getattr(active_encounter, "category", "") == "combat"`)."
  - Implementation: tests pin `category="combat"` → continue and `category="social"` → abandon. Categories beyond combat/social/movement (e.g. a hypothetical `hacking` anchored confrontation) are NOT pinned by a test.
  - Rationale: the story scope is combat; pinning every conceivable future category would be scope creep. The combat-only gate the Reviewer specified naturally makes any non-combat anchored category keep the abandon-on-walk-out semantics — correct for social, acceptable as a known boundary for others until one surfaces in playtest (see Delivery Finding).
  - Severity: minor
  - Forward impact: a future region-mode anchored non-combat confrontation other than social (none ship today) would abandon on a same-region drift, re-hitting the instantiate-then-die loop for that category — revisit if it surfaces.

### Dev (implementation)
- No deviations from spec. The new continue path emits a distinct `confrontation_continued_same_region_drift` watcher event rather than reusing the existing `confrontation_continued_across_location_change`; this is explicitly sanctioned by the TEA assessment (AC2 wildcard `confrontation_continued_*`, matched by prefix — "the fix may reuse the existing ... or mint a distinct same-region variant"). A distinct name keeps the same-region-anchored continue distinguishable from the mobile-chase continue on the GM panel, so it is the better choice, not a spec departure.
- **Round 2 (post-REJECT): no deviations from spec.** Implemented exactly to TEA's RED-rework tests and Dev guidance — (1) gated the continue branch on `category == "combat"` so social/other anchored categories keep abandon-on-walk-out, closing the round-1 scope widening the Reviewer flagged High; (2) hoisted the region-mode flag above the validity gate so a region-mode combat survives a garbage re-title. Both are tightenings the tests demand, not departures.

### Reviewer (audit)
- **Dev's distinct-span-name choice (`confrontation_continued_same_region_drift`)** → ✓ ACCEPTED by Reviewer: TEA-sanctioned AC2 wildcard; a distinct name is better GM-panel diagnostics than reusing the mobile span. Agrees with author reasoning.
- **TEA's AC5 DRIVER-gated proxy** → ✓ ACCEPTED by Reviewer: the live beat/HP half genuinely needs a narrator turn; the two-turn survival proxy is the right unit-level stand-in. AC5 remains DRIVER-gated post-merge.
- **TEA's watcher-event (not OTLP) OTEL assertions** → ✓ ACCEPTED by Reviewer: `_watcher_publish` is the GM-panel channel for this path; synchronous capture is refactor-stable.
- **UNDOCUMENTED deviation (FLAGGED by Reviewer):** TEA's dev guidance said continue "the anchored confrontation" (category-agnostic) and Dev implemented exactly that, but the story scope (title + SM assessment + every AC/test) is **combat-only**. Applying the continue to all anchored categories (incl. `social`) is an undocumented widening of scope beyond the measured bug, and it reintroduces the 2026-04-30 negotiation-walk-out abandon for region-mode social encounters. Spec source: story title / SM Assessment (combat). Code does: continues all non-mobile categories. Severity: **High**. See Reviewer Assessment.

#### Round 2 audit (post-REJECT)
- **Round-1 FLAG → ✓ RESOLVED:** the combat-only gate (`category == "combat"`) closes the scope-widening; social now abandons, pinned by `test_same_region_drift_abandons_social_negotiation_in_region_mode`. The flagged High is fixed.
- **TEA: invalid-heading survival test added beyond the strictly-blocking finding** → ✓ ACCEPTED by Reviewer: closing the [SILENT] invalid-region abandon while the lane is open is sound ("fix it right"); the hoist depends only on pack+world, so it is safe to compute before the validity gate. Sound deviation.
- **TEA: combat-only scope pinned by example (combat continues / social abandons); other anchored categories not pinned** → ✓ ACCEPTED by Reviewer: matches the story's combat scope and my round-1 fix guidance; pinning every hypothetical category would be scope creep. The non-combat-non-social boundary is logged as a non-blocking Delivery Finding — correct disposition.
- **Dev: no deviations from spec (round 2)** → ✓ ACCEPTED by Reviewer: implemented exactly to TEA's tests and guidance; both changes are tightenings the tests demand, verified against the diff.

## Subagent Results

### Round 2 (post-REJECT re-review, 2026-06-09)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (25/25 green serially, ruff check+format clean; notes: inline import + alias style, both pre-existing/cosmetic) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Yes | findings | 7 | confirmed 0, dismissed 4, deferred 3 (all Low/non-blocking) |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none (every ladder arm emits a span; social→else→deactivation span, no silent abandon) | confirmed 0, dismissed 0, deferred 0 |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 1 (MEDIUM, downgraded — see below), dismissed 0, deferred 1 (Low); 4 were "confirming correct, no action" incl. round-1 tautology RESOLVED |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none (narrator string cannot steer continue/abandon; server-side inputs; lazy logging, no PII) | confirmed 0, dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled; 2 with findings)
**Total findings:** 1 confirmed (MEDIUM, non-blocking), 4 dismissed (with rationale), 4 deferred (Low/non-blocking)

**Edge-hunter triage (round 2):**
- L3491 canonicalization-mismatch on `current_region` equality — **deferred Low**: in region-mode worlds `current_region` is always the canonical slug (seeded at region.init; L3188 stores `known_region_id` canonical), so the surface-vs-canonical mismatch cannot arise on the repro path; deterministic tests pass on canonical forms. Not introduced by this diff.
- L3489 `result.location is None` path — **DISMISSED**: the entire abandon block is inside `if result.location:` (L2994); `result.location` is truthy here, never None.
- L3527 `player_metric`/`opponent_metric` None deref — **DISMISSED**: both are required `EncounterMetric` fields (`encounter.py:171-172`, no `| None`); None is impossible, and the identical access predates this story in the mobile-continue branch.
- L3489 category case-sensitivity (`"COMBAT"`) — **deferred Low**: `category` is server-stamped from `ConfrontationDef.category` (authored YAML), not narrator-injected; lowercase by convention, and `_encounter_is_mobile` makes the same case-sensitive assumption (`frozenset({"movement"})`). Consistent with existing code; defensive `.lower()` is a possible future hardening.
- L3015 mutable-ref aliasing — **DISMISSED**: `current_region` is `str|None`.
- test L247 `pc_regions` Linus/Sam — **DISMISSED**: single-PC test-fixture nuance, not a runtime defect.
- L3038 `_region_mode_world_active`/`_is_region_mode_world` alias — **deferred Low**: readability nit; verified the value is not reassigned between the hoist and the elif (Dev removed the duplicate in-else computation).

## Rule Compliance

### Round 2 (re-review) — both round-1 FAILs now resolved

Re-enumerated against `.pennyfarthing/gates/lang-review/python.md` (13 checks) for the round-2 diff.

- **#6 Test quality** — **now PASS.** The round-1 tautological wiring test is gone; `test_same_region_continue_does_not_emit_panel_clear_signal` asserts the real OTEL signature (deactivation span absent + continue span present), confirmed non-tautological by [TEST]. Monkeypatch target (`narration_apply._watcher_publish`) is patched where used — correct. One residual MEDIUM (non-blocking): the new `test_invalid_heading_does_not_abandon_combat_in_region_mode` asserts combat-survives + no-deactivation-span but not the positive continue span — downgraded because the same continue branch's span IS pinned by the sibling AC2 test, and the deactivation-span-absent assertion already falsifies the hoist-revert regression the test targets.
- **#13 Fix-introduced regressions** — **now PASS.** The continue `elif` is gated `category == "combat"`; social/other anchored categories fall through to the abandon branch (span emitted), preserving the 2026-04-30 negotiation-walk-out semantics. The round-1 HIGH (continue widened to all anchored categories) is closed and pinned by `test_same_region_drift_abandons_social_negotiation_in_region_mode` + its OTEL companion.
- **#3 / #10 (hoist delta)** — the hoisted `NavigationMode` import is a pre-existing inline import relocated, not new; `_apply_narration_result_to_snapshot` remains a private helper (annotation-exempt). PASS.
- **#1, #2, #4, #5, #7, #8, #9, #11, #12** — unchanged from round 1 (PASS / N/A as recorded below).

### Round 1 (original enumeration — retained for trail)

Enumerated against `.pennyfarthing/gates/lang-review/python.md` (13 checks) for the two changed `.py` files.

- **#1 Silent exception swallowing** — no `try/except` added. PASS.
- **#2 Mutable default args** — no new function signatures. PASS.
- **#3 Type annotations at boundaries** — `_apply_narration_result_to_snapshot` is a private helper (leading `_`), exempt; new locals need no annotation. PASS.
- **#4 Logging coverage/correctness** — new branch uses `logger.info("...%s...", ...)` lazy `%s`/`%r` (not f-strings); info-level is correct for a continue *decision* (not an error path). PASS.
- **#5 Path handling** — none. N/A.
- **#6 Test quality** — 9 of 11 tests have specific, non-vacuous assertions. TWO violations confirmed: `test_same_region_continue_keeps_dispatch_branch_from_clearing_panel` re-derives handler booleans in-body (not a real wiring test) and its final `assert not (prior_live and not now_live)` is tautological given the prior assertion. See [TEST] findings. FAIL (medium).
- **#7 Resource leaks** — none. N/A.
- **#8 Unsafe deserialization** — none. N/A.
- **#9 Async pitfalls** — function is sync; no async added. N/A.
- **#10 Import hygiene** — no new imports in the diff (reuses `NavigationMode` already imported in-block). PASS.
- **#11 Input validation at boundaries** — `result.location` is Pydantic `str|None`, validated upstream by `validate_region_name`; new flags derive from server-side cartography, not the raw narrator string (confirmed by [SEC]). PASS.
- **#12 Dependency hygiene** — none. N/A.
- **#13 Fix-introduced regressions** — the fix's new `elif` widens continue to ALL non-mobile categories, reintroducing the abandon-on-walk-out semantics removed for social encounters in region-mode worlds. FAIL (high) — see [EDGE].

## Devil's Advocate

Assume this fix is broken. The most damning angle: it does not do what its own story says. The story is titled "Region-mode location-drift abandons live **combat**," every AC and every test fixture builds `category="combat"`, yet the production guard checks only `_region_mode_world_active and current_region unchanged` — it never looks at the encounter category. The mobile branch above it carves out `movement`; everything else falls through. That "everything else" is not just combat. It is `social`, `hacking`, and any future `ConfrontationDef.category`. So the most load-bearing world the project ships — `wry_whimsy/oz`, region-mode, asset-complete, live — runs social negotiations (the Cowardly Lion yield path is referenced *in this very function* at L3416). Picture the table: the party browbeats the Lion in Munchkin Country, then the narrator re-titles the scene to "The Yellow Brick Road — The Poppy Field" (same region, a cosmetic drift). Pre-fix, that abandons the negotiation — correct, they walked away. Post-fix, the four beat buttons stay clickable two locations away from the Lion, and clicking "Threaten" puppets an NPC who isn't there. That is verbatim the 2026-04-30 bug the codebase deliberately fixed, and the comment block memorializing it is *still in the file*. A confused player will click a stale button; a malicious one will farm a cowed NPC forever. A stressed narrator emitting a bracketed aside ("(narrator brief)") flips `validate_region_name` to False, drops `_region_mode_world_active` to its default, and silently abandons a live combat with no causal span — the GM panel shows a rejected heading and a dead fight with no link between them. And the wiring test that is supposed to be the backstop never calls the handler; its terminal assertion reduces to `assert not False`. The unit suite is green, but green here proves only that combat continues — it never exercised the category that breaks. If I am wrong, it is only because social negotiations in region-mode worlds are vanishingly rare in practice — but "rare" is not "tested," and oz is shipping.

### Devil's Advocate — Round 2

Assume the fix is still broken. Where would it hide now? The combat gate is a literal `getattr(active_encounter, "category", "") == "combat"` — no fallback to a pack lookup the way `_encounter_is_mobile` falls back when `category == ""`. So a *legacy* combat encounter (a save predating the `category` field, `category=""`) would now fail the gate and abandon on a same-region drift. Is that the instantiate-then-die bug, resurrected for old saves? I traced it: pre-90-6, that legacy combat abandoned on *every* location-string change — so the gate doesn't *regress* legacy behavior, it merely fails to *improve* it. And the actual repro path — perseus_cloud SWN, the_circuit cwn — instantiates encounters fresh with `category` stamped from the `ConfrontationDef`, so the live worlds hit the `== "combat"` path cleanly. The memory rule ("no saves to migrate") confirms legacy saves are not a concern. Next angle: the hoist runs `pack.worlds.get(world)` on *every* location-update turn now, not just valid-region ones — could a malformed pack throw? `.get()` on a dict returns None for a missing world, and `_make_region_mode_world`/`getattr(..., "cartography", None)` are all None-tolerant; a non-region-mode or absent world yields `_is_region_mode_world=False` and the continue branch never fires — verified by the `world=None` gating guard test (still green). Final angle: the one real gap — the invalid-heading test can't tell "engine continued" from "engine did nothing." But the abandon ladder has no path that leaves a combat unresolved *except* the continue branch (won/yield resolve; mobile is combat≠movement; else abandons+spans), so "combat survived the abandon block" *implies* the continue branch fired. The gap is theoretical, the span is pinned by the sibling AC2 test, and the deactivation-absent assertion already catches the hoist-revert regression the test exists to guard. Nothing here clears the High bar.

## Reviewer Assessment — Round 1 (REJECTED, superseded 2026-06-09)

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [EDGE] [RULE] | New same-region-continue `elif` is not scoped to combat — it continues ALL non-mobile categories, incl. `social`. Reintroduces the 2026-04-30 negotiation-walk-out abandon bug for every region-mode world (oz Cowardly Lion, etc.): a negotiation walked out of within the same region stays live with clickable beats. Out of the story's measured scope (combat). | `sidequest/server/narration_apply.py` ~L3487 (new `elif`) | Gate the `elif` on combat category (e.g. `getattr(active_encounter, "category", "") == "combat"`, or a small `_encounter_is_anchored_combat` helper). Add a test: region-mode world + `category="social"` negotiation + same-region location change → still abandons (or whatever the intended social behavior is, pinned by a test). |
| [MEDIUM] [TEST] | Wiring test re-derives the handler's `prior_live`/`now_live` in its own body and asserts on self-computed values; the final `assert not (prior_live and not now_live)` is tautological (`prior_live=True` hard-set, `now_live` follows from the line-699 assertion → `assert not False`). It re-tests AC1 under a new name; it does not prove handler wiring. | `tests/server/test_region_mode_drift_keeps_combat.py` L572-616 (esp. L613) | Replace with the real signal the dispatch branch keys on: assert `_DEACTIVATED_EVENT not in _event_types(watcher_events)` via the `watcher_events` fixture (the absence of the deactivation span is exactly what keeps the panel open), or drive the real handler and assert no `CONFRONTATION {active:false}` is dispatched. Drop the tautological assert. |
| [MEDIUM] [SILENT] [EDGE] | An invalid narrator heading (`validate_region_name` → False: bracketed/multiline/too_long) in a region-mode world leaves `_region_mode_world_active=False`, so a live combat is abandoned on a garbage re-title with no causal span linking the rejected heading to the lost encounter. Pre-existing behavior, but adjacent to this fix's lane and cheaply closed. | `sidequest/server/narration_apply.py` — assignment at ~L3151 is inside the valid-region `else` only | Compute `_is_region_mode_world` / `_region_mode_world_active` BEFORE the `if not is_valid_region:` gate (it depends only on `pack`+`world`, not the location string), so a region-mode combat survives a garbage re-title too. Optional within this rework but recommended while the lane is open. |

**Dispatch tag coverage:** [EDGE] confirmed (category over-broadening — HIGH; metric-None deref dismissed: `player_metric`/`opponent_metric` are required fields; None==None continue accepted: a real region change always advances `current_region` so it cannot be masked; party-split global-region noted Low/non-blocking, consistent with the single-global-encounter design). [SILENT] confirmed (invalid-region abandon — MEDIUM; the drift-subtype span field suggestion deferred as Low). [TEST] confirmed (tautological wiring test + prefix-match laxity — MEDIUM; None-region and room_graph-world coverage gaps deferred to the rework). [SEC] clean (flags derive from server state, not the narrator string; no PII/injection/deserialization). [DOC] N/A — disabled. [TYPE] N/A — disabled. [SIMPLE] N/A — disabled. [RULE] folded into Rule Compliance (#6 test-quality FAIL, #13 fix-regression FAIL; checker subagent disabled, verified manually).

**Data flow traced:** narrator `result.location` (Pydantic `str|None`) → `validate_region_name` → region-resolution block (sets `current_region`, `_region_mode_world_active`) → encounter-abandon ladder (won → yield → mobile → **same-region-continue** → abandon). The new branch's decision inputs are server-side (`current_region`, cartography), not the raw narrator string — safe from injection, but the category blind spot lets social encounters take the combat path.

**Handoff:** Back to TEA (Amos) for RED rework — the blocking fix requires new category-scoping tests, so this returns to test design, not straight to Dev.

---

## Reviewer Assessment

**Verdict:** APPROVED

Round-2 re-review after my round-1 REJECT. All three round-1 findings are resolved, the five enabled subagents return no confirmed blocking issues, and the diff is GREEN and lint-clean. Severity bar for blocking (Critical/High) is not met.

**Round-1 findings — disposition:**
| Round-1 finding | Status | Evidence |
|-----------------|--------|----------|
| [HIGH][EDGE][RULE] continue not combat-scoped | ✓ RESOLVED | `elif` now gated `(getattr(active_encounter, "category", "") or "") == "combat"` (`narration_apply.py:3492`); social falls through to abandon. Pinned by `test_same_region_drift_abandons_social_negotiation_in_region_mode` + OTEL companion (social emits deactivation, not continue). |
| [MEDIUM][TEST] tautological wiring test | ✓ RESOLVED | Repaired as `test_same_region_continue_does_not_emit_panel_clear_signal`; asserts deactivation-span-absent + continue-span-present. [TEST] confirms non-tautological, monkeypatch target correct. |
| [MEDIUM][SILENT][EDGE] invalid heading abandons combat | ✓ RESOLVED | `_is_region_mode_world`/`_region_mode_world_active` hoisted above the validity gate (`narration_apply.py:~3026`); combat now survives a rejected heading. Pinned by `test_invalid_heading_does_not_abandon_combat_in_region_mode`. |

**Remaining findings (non-blocking):**
| Severity | Issue | Location | Disposition |
|----------|-------|----------|-------------|
| [MEDIUM][TEST] | invalid-heading test asserts combat-survives + no-deactivation-span but not the positive `confrontation_continued_*` span | `test_region_mode_drift_keeps_combat.py` | Non-blocking — same continue branch's span is pinned by the sibling AC2 test, and the deactivation-absent assertion already falsifies the hoist-revert regression the test targets. Hardening logged as a Delivery Finding. |
| [LOW][TEST] | AC4 mobile real-region-change path has no OTEL companion test | `test_region_mode_drift_keeps_combat.py:~424` | Non-blocking — the mobile continue path predates this story; deferred. |
| [LOW] | combat gate is a literal `== "combat"` with no pack-lookup fallback for legacy `category==""` | `narration_apply.py:~3492` | Non-blocking — live worlds stamp category at instantiation; no saves to migrate. Symmetric helper logged as a Delivery Finding. |
| [LOW][EDGE] | `current_region` equality assumes canonical form on both sides | `narration_apply.py:3491` | Non-blocking — region-mode worlds always store the canonical slug; not introduced by this diff. |

**Dispatch tag coverage:** [EDGE] 7 findings, 0 confirmed blocking — 4 dismissed (None-location guarded by `if result.location:` L2994; metric-None impossible, required `EncounterMetric` fields; str|None aliasing; test-fixture nuance), 3 deferred Low (canonicalization, category case, name-alias). [SILENT] **clean** — every arm of the abandon ladder emits a `_watcher_publish` span; social→else→`confrontation_deactivated_on_location_change`, no silent abandon. [TEST] round-1 tautology RESOLVED; 1 MEDIUM (downgraded, non-blocking) + 1 LOW deferred. [SEC] **clean** — the continue/abandon decision keys on server-side state (`current_region`, cartography, `category`); the narrator string reaches it only via `_resolve_heading_to_cartography` against a closed authored catalog (a region-matching heading advances `current_region` → abandon, defeating any keep-alive exploit); lazy logging, no PII. [DOC] N/A — disabled. [TYPE] N/A — disabled. [SIMPLE] N/A — disabled (preflight noted inline import + name-alias as cosmetic, non-blocking). [RULE] folded into Rule Compliance — round-1 #6 and #13 FAILs both now PASS.

**Data flow traced:** narrator `result.location` (Pydantic `str|None`, truthy inside `if result.location:`) → `validate_region_name` → region-mode flag (now hoisted, reads only pack+world) → region-resolution may advance `current_region` only on an authored-catalog match → encounter-abandon ladder (won → yield → mobile → **same-region combat continue** → else abandon). Decision inputs are server-side; the combat gate correctly scopes the continue to the measured bug.

**Pattern observed:** the combat-only gate mirrors the existing `_encounter_is_mobile` carve-out one branch above — consistent ladder structure (`narration_apply.py:~3456` mobile, `~3489` same-region combat, `~3535` else abandon).

**Error handling:** the hoisted flag computation is None-tolerant at every `getattr`/`.get`; absent pack/world → `_is_region_mode_world=False` → continue branch never fires → existing abandon path (verified by the `world=None` gating guard, green).

**Tests:** 25/25 GREEN serially (`-n0`), `ruff check`/`format` clean (preflight).

**Handoff:** To SM (Camina Drummer) for finish-story.