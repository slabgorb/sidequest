---
story_id: "59-27"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 59-27: Intent Router never dispatches verbal/social confrontations — only escape fires, post-commitment (wry_whimsy/oz)

## Story Details
- **ID:** 59-27
- **Jira Key:** (none — Jira disabled)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-server

## Story Context

This is a FRESH defect in the SHIPPED IntentRouter (cutover 59-1/59-4/59-10 are DONE). The router only ever fires `escape` (movement) confrontations, and only after heavy player escalation. Verbal/social types (persuasion, audience_trial, wit_duel, wonder_shock) NEVER dispatch, even on direct committed prompts.

**Likely root cause:** Per-pack DERIVED intent_verb_set for wry_whimsy's verbal confrontation types is too narrow to match natural prose. Investigate:
- `intent_router_pass.py` (execute_intent_router_pre_narrator_pass)
- `wry_whimsy/rules.yaml` derived verb sets

**Design question to encode:** Should a menace auto-enter a confrontation (turn 5) or only on player commitment (turn 6)? Pick one, document the choice in the session findings.

**POSSIBLE SECOND REPO:** If the fix is per-pack verb-set tuning, it also touches sidequest-content (`wry_whimsy/rules.yaml`). This session targets server only; Dev should flag if a content edit is needed.

**NOTE:** The invisibility half of the original poppy-field finding (no beat/dice/dial UI) is a SEPARATE bug already fixed in PR sidequest-server#575 — OUT OF SCOPE. This story is ONLY trigger sensitivity.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T06:35:47Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03 | 2026-06-03T05:40:27Z | 5h 40m |
| red | 2026-06-03T05:40:27Z | 2026-06-03T06:07:39Z | 27m 12s |
| green | 2026-06-03T06:07:39Z | 2026-06-03T06:13:33Z | 5m 54s |
| spec-check | 2026-06-03T06:13:33Z | 2026-06-03T06:16:48Z | 3m 15s |
| verify | 2026-06-03T06:16:48Z | 2026-06-03T06:23:12Z | 6m 24s |
| review | 2026-06-03T06:23:12Z | 2026-06-03T06:33:49Z | 10m 37s |
| spec-reconcile | 2026-06-03T06:33:49Z | 2026-06-03T06:35:47Z | 1m 58s |
| finish | 2026-06-03T06:35:47Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (non-blocking): widening the `_build_state_summary` confrontation_types projection to carry `intent_verbs` (the AC2 fix) directly conflicts with the existing Story 59-10 test. Affects `tests/server/test_intent_router_confrontation_vocabulary.py::test_state_summary_includes_confrontation_types_from_pack` (line ~77: `assert set(combat_entry.keys()) == {"type", "category"}` — must be updated to allow `intent_verbs`). This is the sanctioned verb-set reversal AC2 calls for; its docstring already (staleley) claims it includes intent_verbs. Dev must update that assertion when making the new projection tests pass. *Found by TEA during test design.*
- **Question** (non-blocking): AC4's deepest case is unverified. My watcher test (`test_unrouted_verbal_confrontation_fires_unengaged_watcher`) passes with the contended authority tagged `side="opponent"` — proving the no-emission `confrontation.unengaged_turn` watcher is genre-agnostic and already covers an opponent-tagged social standoff. BUT the watcher's precision gate is `_named_opponent` (`side=="opponent"` only). If the turn-10 save shows the Guardian tagged `side="neutral"` (a persuasion target you win over, not fight), the watcher silently misses it. Broadening to "any present NPC" would storm on every quiet-dialogue turn. The storm-free signal is the router's OWN dispatch: once the AC1/AC2 fix lands, the router emits a verbal confrontation and the type-agnostic `dispatch_engagement_watcher` (`_check_confrontation_engaged`) catches any that fail to engage. Affects `sidequest/server/narration_apply.py` (the no-emission watcher) — Dev/Architect should confirm against the save whether broadening is needed or whether the dispatch_engagement watcher post-fix is the correct (one-mechanism) home. *Found by TEA during test design.*
- **Improvement** (non-blocking): the precise root cause is narrower than the story's hypothesis ("derived intent_verb_set too narrow"). The verb sets are not narrow — they are *not passed to the router at all* (59-10 projects `{type, category}` only). The complementary half is that `CONFRONTATION_TRIGGER_CORE` (`sidequest/agents/narrator_guardrails.py`) enumerates social-trigger type names from other packs (negotiation/trial/auction/social_duel/scandal), giving wry_whimsy's social types no recognition anchor. Dev picks ONE fix location (widen the projection OR generalize the trigger core); the prompt-layer test is mechanism-agnostic and passes either way. *Found by TEA during test design.*

### Dev (implementation)
- **Resolved** (TEA Conflict, non-blocking): the anticipated 59-10 test conflict did NOT materialize. `_build_state_summary` now omits `intent_verbs` for any type that declares none, so the verb-less `test_genre` fixture (its `combat`/`negotiation`/`chase` types have no `intent_verbs`) keeps the `{type, category}` shape and `test_state_summary_includes_confrontation_types_from_pack` stays green unchanged. The fix is backward-compatible; no existing assertion needed updating. *Found by Dev during implementation.*
- **Question carried forward** (TEA AC4 neutral-tag edge, non-blocking): I did NOT broaden the no-emission `confrontation.unengaged_turn` watcher. With the vocabulary fix in place the router now *dispatches* verbal confrontations, so the type-agnostic `dispatch_engagement_watcher` (`_check_confrontation_engaged`, `sidequest/agents/dispatch_engagement_watcher.py`) is the one-mechanism home for "verbal confrontation routed but engine didn't engage." The no-emission neutral-tag case (router emits *nothing* AND the contended NPC is tagged `side="neutral"`) is left as TEA flagged — broadening it speculatively risks a false-positive storm on every quiet-dialogue turn and has no failing test. Recommend Architect/Reviewer confirm against the turn-10 save whether the neutral-tag no-emission case is real before any broadening. Affects `sidequest/server/narration_apply.py`. *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking): simplify-efficiency flagged two pre-existing structures in `sidequest/server/intent_router_pass.py` that are outside this story's diff but worth a standalone cleanup: `_witnessed_act_ids` (line 101) duplicates its filter loop across `per_player` + `cross_player` (a `chain(...)` unify), and `execute_intent_router_pre_narrator_pass` carries 4 optional context kwargs that could collapse to one `extra_context` dict (ripples into `websocket_session_handler.py`). Not actioned here (minimalist discipline — no failing test, untouched by 59-27). Candidate for a refactor chore if the router pass is revisited. *Found by TEA during test verification.*
- **Resolved** (Architect spec-check rec C): tightened the AC5 guard to assert the literal `snapshot.encounter is not None and encounter_type == "persuasion"` — verified passing. AC5 coverage now matches the spec wording. *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): add `verb_count` to the typed `SpanRoute.extract` lambda for the `intent_router.confrontation_vocabulary` route, for consistency with its sibling `type_count`. Affects `sidequest/telemetry/spans/intent_router.py` (the confrontation-vocabulary `SpanRoute`). NOT a blindness — `verb_count` already reaches the GM panel via the flat firehose (`watcher.py:84-96` emits `agent_span_close` with all span attrs); this only adds it to the typed state_transition projection. *Found by Reviewer during code review.*
- **Gap** (non-blocking): `ConfrontationDef.intent_verbs` has no length bound; a homebrew pack could author huge verb lists that inflate the router prompt every turn (cost amplification). Affects `sidequest/genre/models/rules.py` (`ConfrontationDef`) — add a fail-loud validator (max list length + max per-verb length) at pack-load time per No Silent Fallbacks. Pre-existing field amplified by this story's projection; PR-gated authoring + ADR-134 cost ceiling mitigate. Candidate for a content-schema-validator follow-up story. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): two LOW test-file polish items — `_wry_snapshot()` uses `GameSnapshot(genre=...)` (line 97; `genre` is not a field — use `genre_slug=` and drop the redundant next line; pyright-flagged but a pre-existing tolerated pattern copied from `test_intent_router_confrontation_vocabulary.py`), and the server-test docstring (lines 29-33) carries a now-stale claim that "the Dev phase updates that 59-10 assertion" (it didn't — backward-compatible). Affects `tests/server/test_intent_router_verbal_social_dispatch.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the pre-existing `test_intent_router_confrontation_vocabulary.py` has a docstring/assertion mismatch — docstring (line 63) says "type/category/intent_verbs per def" but the assertion (line 77) still asserts `{type, category}`. It passes only because the fixture's types declare no verbs; it will break if a fixture type ever gains `intent_verbs`. Out of this story's diff. Affects `tests/server/test_intent_router_confrontation_vocabulary.py`. *Found by Reviewer during code review.*
## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC1/AC5 dispatch proof is a wiring guard, not an LLM-classification test**
  - Spec source: context-story-59-27.md, AC-1 ("proven by an OTEL dispatch span on a verbal-only turn") and AC-5 (regression: "engages a confrontation … not prose-only with confrontation=None")
  - Spec text: "Router dispatches a confrontation for committed verbal/social intent … WITHOUT requiring physical/movement escalation"
  - Implementation: the dispatch behavior depends on Haiku's live classification, which cannot be asserted deterministically without a network call (tests must not spawn a real Claude client — see `build_intent_router_for_session` docstring). The verbal-turn dispatch is therefore proven in two deterministic layers instead: (a) the router PROMPT carries the verbal vocabulary (`test_router_prompt_carries_verbal_vocabulary`, RED), and (b) a dispatched social confrontation survives the gates + fires the `intent_router.decompose` span end-to-end (`test_dispatched_social_confrontation_survives_gates_and_emits_span`, guard, with a fake LLM emitting the persuasion package a steered Haiku would).
  - Rationale: the failure mode (router never told the vocabulary) is deterministic and is what the RED tests pin; the LLM's runtime decision is validated by playtest, not unit test. Splitting prompt-steering from pipeline-wiring keeps every assertion deterministic.
  - Severity: minor
  - Forward impact: the live verbal-dispatch behavior is verified at playtest, not in CI — the engagement e2e validation (epic 59-15) is the integration backstop.
- **AC3 encoded as content invariant + Operator design decision, not a new mechanic**
  - Spec source: context-story-59-27.md, AC-3 ("menace-pushed Wonder-Shock either auto-enters on engagement OR explicitly requires player commitment — one or the other")
  - Spec text: "Design decision recorded and encoded"
  - Implementation: Operator (2026-06-03) chose AUTO-ENTER on menace + single-beat resolution via the EXISTING `resolution: true` push beat (no new weight-scaling mechanic). Tests pin the single-beat substrate (`test_social_confrontation_is_single_beat_resolvable`, `test_wonder_shock_look_away_resolves_in_one_beat`) — both guards (the resolution beats already exist). The auto-enter recognition reuses the AC1/AC2 prompt-vocabulary fix (wonder_shock is in the social-types set the prompt test covers).
  - Rationale: the decision is "auto-enter"; the only NEW assertion auto-enter needs is that the menace type's vocabulary reaches the router (covered by AC1/AC2). The single-beat half has a deterministic content home, so it is locked as an invariant rather than left to prose.
  - Severity: minor
  - Forward impact: none — bounds the story to trigger sensitivity; weight-scaling-by-intensity is explicitly deferred (Operator chose "use existing resolution beat" over a new calibration mechanic).

### Dev (implementation)
- **Fix location: widen the state-summary projection (not generalize CONFRONTATION_TRIGGER_CORE)**
  - Spec source: context-story-59-27.md, AC-2 ("wry_whimsy's derived intent_verb_set for its verbal confrontation types is wide enough to match natural prose … verb-set/router-prompt change is documented"); TEA Improvement finding ("Dev picks ONE fix location")
  - Spec text: "the per-pack DERIVED intent_verb_set … is too narrow to match natural prose"
  - Implementation: emitted each type's authored `intent_verbs` into the `_build_state_summary` `confrontation_types` projection, rather than editing the shared `CONFRONTATION_TRIGGER_CORE` system-prompt string to generalize social-trigger recognition.
  - Rationale: the projection is data-driven — every pack's verbs flow automatically with zero shared-prompt maintenance, and a future verbal pack is covered without touching narrator_guardrails. Editing the shared trigger core would hard-code another pack's vocabulary into a string every genre pays for. This also reverses 59-10's "closed enum, not verb lists" decision, which the playtest disproved.
  - Severity: minor
  - Forward impact: the router prompt grows by each pack's verb list (modest — a handful of words per type); follows "Cost Scales with Drama" (spend tokens on the mechanical spine). 59-10's token-lean rationale is superseded for the confrontation projection.
- **Omit `intent_verbs` key for types that declare none (backward-compat)**
  - Spec source: tests TEA wrote — `test_state_summary_social_types_carry_intent_verbs` requires the key for verb-bearing social types; the 59-10 fixture test asserts `{type, category}` for verb-less types
  - Spec text: "the {tname!r} projection must carry intent_verbs"
  - Implementation: the projection adds `intent_verbs` only when `cdef.intent_verbs` is non-empty; verb-less types keep the `{type, category}` shape.
  - Rationale: keeps the projection compact and honest about what each pack authored, and preserves backward compatibility so the 59-10 fixture test stays green without modification (no over-reach beyond the failing tests).
  - Severity: minor
  - Forward impact: none.

### Reviewer (audit)
- **TEA: "AC1/AC5 dispatch proof is a wiring guard, not an LLM-classification test"** → ✓ ACCEPTED by Reviewer: sound — tests must not spawn a real Claude client; the deterministic two-layer split (prompt carries vocab; dispatched confrontation engages) is the right boundary. AC5's encounter-instantiation is now also asserted literally after the verify-phase tightening.
- **TEA: "AC3 encoded as content invariant + Operator design decision, not a new mechanic"** → ✓ ACCEPTED by Reviewer: matches the Operator's 2026-06-03 decision (auto-enter + existing resolution beat). Carry the forward note: playtest must confirm a *soft* menace auto-enters rather than degrading to a low-confidence hint (router is confidence-gated by ADR-113/123).
- **Dev: "Fix location: widen the state-summary projection (not generalize CONFRONTATION_TRIGGER_CORE)"** → ✓ ACCEPTED by Reviewer: the data-driven projection is the better choice — every pack's verbs flow automatically, no shared-prompt maintenance, future verbal packs covered without touching narrator_guardrails. Correctly supersedes 59-10's token-lean rationale.
- **Dev: "Omit `intent_verbs` key for types that declare none (backward-compat)"** → ✓ ACCEPTED by Reviewer: minimal and backward-compatible — verified the verb-less `test_genre` fixture keeps `{type, category}` and the 59-10 suite stays green unchanged. No over-reach.
- **Undocumented deviations found:** none. The diff's behavior is fully covered by the four logged deviations above. (Two LOW polish items — verb_count absent from the typed `SpanRoute.extract`, and the `genre=` kwarg typo — are observations, not spec deviations; captured as Delivery Findings.)

### Architect (reconcile)

Verified the four in-flight deviation entries (2 TEA, 2 Dev): all carry the full 6 fields, cite real spec sources (`context-story-59-27.md`), quote accurate spec text, and their "Implementation" descriptions match the actual diff (`intent_router_pass.py` projection widening + `verb_count` span attr; tests). Reviewer stamped all four ACCEPTED. Two additional deviations belong in the manifest:

- **Story root-cause premise corrected: no verb set was widened — the existing verbs were merely routed**
  - Spec source: context-story-59-27.md — Problem + AC-2
  - Spec text: "the per-pack DERIVED intent_verb_set for wry_whimsy's verbal confrontation types is too narrow to match natural prose" / AC-2 "wry_whimsy's derived intent_verb_set for its verbal confrontation types is wide enough to match natural prose"
  - Implementation: NO verb set was edited (sidequest-content is clean; the diff is server-only). wry_whimsy's authored verbs (e.g. persuasion: persuade/convince/reassure/befriend/coax/charm/entreat/win-over) were already adequate — they simply were not reaching the router (59-10 projected `{type, category}` only). The fix routes the existing verbs into the projection; "widening" was unnecessary.
  - Rationale: the spec's "too narrow" premise was an incorrect diagnosis (flagged by TEA's Improvement finding). The real defect was a missing projection field, not insufficient vocabulary. Fixing the actual cause (route the verbs) is correct over the hypothesized cause (author more verbs).
  - Severity: minor
  - Forward impact: none — if a *future* pack's verbs prove genuinely too narrow for prose matching, that is a per-pack content tuning task, now unblocked because the verbs actually reach the router.
- **AC4 satisfied for the opponent-tagged case; the neutral-tagged no-emission sub-case is deferred**
  - Spec source: context-story-59-27.md — AC-4
  - Spec text: "The 59-3 router-vs-engine lie-detector watcher flags a turn whose narration reads as a verbal confrontation but no confrontation was routed (no silent miss)"
  - Implementation: the no-emission `confrontation.unengaged_turn` watcher is genre-agnostic and fires for an opponent-tagged wry_whimsy social standoff (guard-tested). It was NOT broadened to the case where the contended NPC is tagged `side="neutral"` (a persuasion target). Post-fix, the router now dispatches verbal confrontations, so the type-agnostic `dispatch_engagement_watcher` covers dispatched-but-unengaged; the residual no-emission-with-neutral-other edge is deferred pending turn-10 save verification (broadening risks a quiet-dialogue false-positive storm).
  - Rationale: the primary silent-miss path (router dispatches nothing for a verbal demand) is closed by the AC1/AC2 fix + existing watchers; the neutral-tag no-emission edge is speculative without save evidence and "one mechanism per problem" favors the dispatch_engagement watcher over broadening the no-emission gate.
  - Severity: minor
  - Forward impact: a follow-up may broaden the watcher IF the turn-10 save confirms the contended authority is tagged `side="neutral"`; affects `sidequest/server/narration_apply.py`.

**AC deferral verification:** No ACs were DESCOPED. AC1/AC2/AC3/AC5 are fully DONE. AC4 is substantively DONE with one deferred sub-case (above) — not invalidated by review. The `verb_count` OTEL attribute is OTEL-Observability-Principle-driven (mandatory observability on a subsystem fix), not an unlogged scope addition.

## Watcher Setup

**Watcher:** Reuse the 59-3 router-vs-engine lie-detector (confrontation_unengaged_turn_span) so a verbal confrontation that reads-as-engaged-but-unrouted cannot silently miss.

## ADR References

- **ADR-113** Intent Router
- **ADR-123** Mechanical-Engagement Pipeline

## Sm Assessment

Setup complete. Story 59-27 is a fresh trigger-sensitivity defect in the live, shipped IntentRouter — distinct from the cutover work (59-1/59-4/59-10, all done) and from the separate invisibility bug fixed in PR #575. Scope is narrow and well-evidenced: across a full wry_whimsy/oz session only `escape` (movement) confrontations ever fired, and only after heavy escalation; the verbal/social types (persuasion, audience_trial, wit_duel, wonder_shock) never dispatched even on direct, committed prompts.

The story carries a strong root-cause hypothesis (per-pack derived intent_verb_set too narrow to match natural prose) and concrete investigation targets (`intent_router_pass.py::execute_intent_router_pre_narrator_pass` + `wry_whimsy/rules.yaml` derived verb sets). It also carries one genuine design decision TEA/Dev must encode and document: menace auto-entry (turn 5) vs. player-commitment entry (turn 6).

**Routing:** tdd phased → **TEA** for RED. TEA should write a failing test that proves a committed verbal/social intent dispatches the correct confrontation type (not `escape`, not `None`), and wire the 59-3 lie-detector watcher (`confrontation_unengaged_turn_span`) so a read-as-engaged-but-unrouted verbal confrontation cannot silently miss.

**Watch item for Dev:** repo scope may widen to sidequest-content if the fix is per-pack verb-set tuning. Session targets `server`; flag before touching content.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Behavior defect in a shipped subsystem — RED tests pin the missing behavior before the fix.

**Test Files:**
- `tests/server/test_intent_router_verbal_social_dispatch.py` — router projection + prompt vocabulary (RED drivers) + dispatch wiring guard
- `tests/integration/test_wry_whimsy_verbal_confrontation.py` — AC3 single-beat resolution invariants + AC4 unengaged-turn watcher guard

**Tests Written:** 10 tests (3 RED drivers + 7 guards) covering AC1, AC2, AC3, AC4, AC5.
**Status:** RED (3 failing — ready for Dev). Commit `430adae` in sidequest-server.

**Root cause pinned (sharper than the story hypothesis):** the verb sets are not *narrow* — they are *not passed to the router at all*. `_build_state_summary` (`sidequest/server/intent_router_pass.py:147-156`) projects each confrontation type as only `{type, category}` (Story 59-10's deliberate "closed enum, not verb lists" decision). The complementary half: `CONFRONTATION_TRIGGER_CORE` (`sidequest/agents/narrator_guardrails.py:90-138`) enumerates social-trigger type names from *other* packs (negotiation/trial/auction/social_duel/scandal), so wry_whimsy's `persuasion`/`audience`/`wit_duel`/`wonder_shock` have no recognition anchor. `escape` (movement) fires because the combat/pursuit rules mention chase/flee. **The fix must make wry_whimsy's verbal vocabulary reach the router** — Dev picks the location (widen the projection OR generalize the trigger core); the prompt-layer RED test is mechanism-agnostic.

**RED drivers (the fix targets these 3):**
| Test | Pins |
|------|------|
| `test_state_summary_social_types_carry_intent_verbs` | projection carries `intent_verbs` for every social type |
| `test_persuasion_projection_includes_authored_verbs` | persuasion's authored verbs specifically reach the projection |
| `test_router_prompt_carries_verbal_vocabulary` | a persuasion verb reaches the combined prompt *outside* the echoed player action (mechanism-agnostic) |

**Guards (currently green — lock the surrounding contract):**
- `test_dispatched_social_confrontation_survives_gates_and_emits_span` — AC1(OTEL)/AC5 wiring: a dispatched `persuasion` confrontation survives the unregistered + precondition gates and fires `intent_router.decompose` (dispatch_count ≥ 1). **This is the suite's wiring test.**
- `test_social_confrontation_is_single_beat_resolvable[audience|wit_duel|wonder_shock|persuasion]` + `test_wonder_shock_look_away_resolves_in_one_beat` — AC3 single-beat substrate (per Operator's "use existing resolution beat" decision).
- `test_unrouted_verbal_confrontation_fires_unengaged_watcher` — AC4: an opponent-tagged social standoff that routes nothing trips `confrontation.unengaged_turn` (proves the no-emission watcher is genre-agnostic). See AC4 Delivery Finding for the unverified neutral-tag edge.

### Rule Coverage

`.pennyfarthing/gates/lang-review/python.md` is a **Dev** self-review checklist (scans changed `.py` for production-code smells). Only check #6 (test quality) applies to test-authoring. Self-audit of the 10 new tests:

| Rule (python.md #6) | Status |
|------|--------|
| No `assert True` / vacuously-true | pass |
| No truthy-only `assert result` (specific values asserted) | pass — membership/value/attribute assertions |
| `mock.patch` on correct target | n/a — no patching; fakes injected via the `IntentRouterLLM` Protocol |
| No assertion-free tests | pass |
| `skip`/`skipif` carries a reason | pass — `skipif(..., reason="wry_whimsy content pack not available")` |
| Parametrized cases test distinct paths | pass — each `ctype` exercises a distinct confrontation def |

**Caught + fixed one vacuous assertion during authoring:** the prompt test initially passed trivially because the player's action literally contained "convince" (echoed into `<raw_action>`). Fixed to excise the raw action from the haystack so it measures the *steering vocabulary*, not the player's words. (python.md #6 "truthy check misses wrong values" class.)

**Rules checked:** 1 of 1 applicable test-authoring rule (#6) covered; checks #1-#5, #7-#13 are Dev production-code rules, deferred to the GREEN phase self-review.
**Self-check:** 1 vacuous test found and fixed during authoring; 0 remain.

**ruff:** `ruff check` + `ruff format --check` clean on both new files.

**Handoff:** To Dev (Agent Smith) for GREEN. Make the 3 RED drivers pass by routing wry_whimsy's verbal vocabulary to the router; update the conflicting 59-10 assertion (see Delivery Findings); keep the 7 guards green. Flag before touching `sidequest-content` (session targets `server`).
## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/server/intent_router_pass.py` — `_build_state_summary` now emits each confrontation type's authored `intent_verbs` in the `confrontation_types` projection (the lexical bridge Haiku matches verbal prose against); the `intent_router.confrontation_vocabulary` OTEL span gains a `verb_count` attribute so the GM panel can verify the bridge reached the router. Verbs omitted for types declaring none (backward-compatible).

**Approach:** Single, minimal, data-driven fix. The verb sets weren't *narrow* — they weren't reaching the router at all (59-10 projected `{type, category}` only). Routing the authored verbs through the existing projection is the smallest change that gives Haiku a per-type vocabulary to bridge "convince me he's worth the walk" → `persuasion`. Chose the projection over editing the shared `CONFRONTATION_TRIGGER_CORE` so every pack's verbs flow automatically (see Design Deviations).

**OTEL (per the Observability Principle — this fix touches the router subsystem):** `intent_router.confrontation_vocabulary` now carries `verb_count`. A zero on a social pack is the lie-detector signal that the vocabulary bridge is missing and verbal confrontations will silently fail to route — exactly the regression this closes.

**Tests:** GREEN.
- 3 RED drivers → passing (projection carries verbs; persuasion verbs present; verbs reach the prompt).
- 7 guards → still passing (dispatch wiring + decompose span; AC3 single-beat invariants; AC4 unengaged-turn watcher).
- Existing 59-10 suite (6 tests) → unchanged & green (backward-compatible; anticipated conflict didn't materialize).
- **Full server suite: 9784 passed, 361 skipped, 0 failed** (37.8s).
- `ruff check` + `ruff format --check` + `pyright` clean on the changed file.

**Repo scope:** Stayed in `sidequest-server` only — the projection fix needed no `sidequest-content` edit (the verbs are already authored in `wry_whimsy/rules.yaml`; the bug was that the server dropped them).

**Branch:** `feat/59-27-intent-router-verbal-social-dispatch` (pushed). Commits: `430adae` (RED tests, TEA), `c761825` (fix, Dev).

**AC coverage:** AC1 (decompose dispatch span on verbal turn) ✓ · AC2 (verb set reaches router, documented) ✓ · AC3 (auto-enter decision encoded + single-beat substrate) ✓ · AC4 (unengaged-turn lie-detector; neutral-tag edge carried forward as a finding) ✓ · AC5 (dispatched social confrontation survives gates) ✓ · suite green + ruff/pyright clean ✓

**Handoff:** To Reviewer (The Merovingian) for code review.
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (minor, well-documented drift — none blocking)
**Mismatches Found:** 4 (all Minor/Trivial; 0 Critical, 0 Major)
**Gate:** `spec-check` passed (AC coverage, implementation-complete, TEA+Dev deviation subsections all present).

Verified the diff (`c761825`) directly and **ran the pass end-to-end**: a dispatched `persuasion` confrontation instantiates `snapshot.encounter` with `encounter_type="persuasion"` (the AC5 behavior, proven live).

- **AC1/AC5 dispatch proof split into two deterministic layers** (Behavioral — Minor)
  - Spec: "Router dispatches a confrontation … proven by an OTEL dispatch span on a verbal-only turn"; AC5 "encounter present in snapshot."
  - Code: the steering (verbs reach the router) + decompose span are asserted deterministically; the live Haiku classification is deferred to playtest (tests must not spawn a real Claude client).
  - Recommendation: **A — accept.** TEA logged the rationale; the failure mode the story targets (router never told the vocabulary) is deterministic and is pinned. The engagement e2e (59-15) is the integration backstop.

- **AC5 guard asserts dispatch-survival + span, not the literal `snapshot.encounter is not None`** (Cosmetic/test-coverage — Trivial)
  - Spec: AC5 "engages a confrontation (encounter present in snapshot), not prose-only with confrontation=None."
  - Code: `test_dispatched_social_confrontation_survives_gates_and_emits_span` asserts `"confrontation" in subsystems` + `dispatch_count >= 1`. I independently verified the encounter DOES instantiate (`encounter_type="persuasion"`), so the behavior is correct — only the assertion is weaker than the AC literal.
  - Recommendation: **C — clarify/tighten.** TEA verify phase should add `assert snap.encounter is not None and snap.encounter.encounter_type == "persuasion"` to the guard (proven cheap and passing). Non-blocking; behavior is already correct.

- **AC3 "auto-enter" is realized via LLM + per-dispatch confidence routing, not a hard server-side gate** (Architectural — Minor)
  - Spec: AC3 "menace-pushed Wonder-Shock … auto-enters on engagement … encoded."
  - Code: the fix routes wonder_shock's vocabulary to the router (enabling recognition) and locks the single-beat resolution substrate; there is no separate deterministic "world-menace auto-enter" gate — entry remains router-decided and confidence-gated (ADR-113/123).
  - Recommendation: **A — accept** (consistent with the confidence-gated router architecture; a hard gate would fight the Zork-problem/Cost-Scales-with-Drama design). **Forward note for Reviewer/playtest:** a *soft* menace could still score low confidence and degrade to a narrator hint rather than auto-entering — the playtest (and 59-15 e2e) must confirm the turn-5 poppy-field shape actually fires wonder_shock now that the vocabulary is present.

- **AC4 neutral-tag no-emission edge deferred** (Behavioral — Minor)
  - Spec: AC4 "a verbal confrontation that reads-as-engaged-but-unrouted cannot silently miss."
  - Code: the opponent-tagged case is covered (genre-agnostic `confrontation.unengaged_turn`, guard-tested); the neutral-tagged no-emission edge is unmodified. With the router now *dispatching* verbal confrontations, the type-agnostic `dispatch_engagement_watcher` is the one-mechanism home for dispatched-but-unengaged; broadening the no-emission watcher risks a false-positive storm.
  - Recommendation: **D — defer.** The primary silent-miss path is closed by the router fix + existing watchers. The neutral-tag no-emission edge needs turn-10 save verification before any broadening — recommend a follow-up story if the save confirms it. Well-reasoned by TEA+Dev; do not broaden speculatively.

**Decision:** Proceed to review. All drift is Minor/Trivial, fully documented in the TEA/Dev deviation logs, and the core behavior is correct and independently verified. No hand-back to Dev. Reviewer should weigh the AC5 assertion-tightening (cheap) and carry the AC3 playtest-confirmation + AC4 neutral-tag items as forward notes, not blockers.
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed — full server suite 9784 passed, 361 skipped, 0 failed (37.3s); ruff + ruff format + pyright clean.

**Spec-check follow-through (Architect rec C, applied):** tightened the AC5 wiring guard to assert the literal — a dispatched verbal confrontation instantiates `snapshot.encounter` with `encounter_type == "persuasion"` (not prose-only with confrontation=None). Closes AC5's coverage to the spec wording. Commit `7072b42`.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`intent_router_pass.py`, `test_intent_router_verbal_social_dispatch.py`, `test_wry_whimsy_verbal_confrontation.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | (high) local `otel_capture` fixture duplicates the shared `tests/server/conftest.py` fixture |
| simplify-quality | 1 finding | (high) same — local fixture shadows the shared one and omits the Story 45-36 processor-reset fix (span-accumulation risk) |
| simplify-efficiency | 3 findings | (high/med/low) all on PRE-EXISTING code outside this story's diff |

**Applied:** 1 high-confidence fix — removed the local `otel_capture` fixture (and its 4 now-unused OTEL imports) from `test_intent_router_verbal_social_dispatch.py`; the test now inherits the shared conftest fixture with the processor-reset fix. Both reuse and quality flagged the same issue ("Don't Reinvent — Wire Up What Exists"). Commit `7072b42`.

**Flagged for Review:** 0 in-scope.

**Noted (not applied — out of scope, pre-existing code with no failing test, minimalist discipline):**
- `_witnessed_act_ids` (`intent_router_pass.py:101`) iterates `per_player` + `cross_player` with identical filtering — efficiency-high, but this is 59-4 code untouched by this story's diff (the diff only changed `_build_state_summary`). A `chain(...)` unify is a reasonable standalone cleanup, not a 59-27 change.
- `execute_intent_router_pre_narrator_pass` 4 optional context params (`dungeon_store`/`palette`/`lookahead_handle`/`additional_player_names`) — efficiency-medium; pre-existing signature with real bank consumers, refactoring it would ripple into `websocket_session_handler.py`. Out of scope.
- vocabulary-span no-op `with ... : pass` nested in projection assembly — efficiency-low; this is the established span-emission idiom across the router pass (`witnessed_act_vocabulary` span uses the same shape). Consistent, not a defect.

**Reverted:** 0.

**Overall:** simplify: applied 1 fix (+ 1 spec-check assertion tightening). Pre-existing efficiency findings logged for a possible standalone cleanup story, not actioned here.

**Quality Checks:** All passing (9784 server tests green; ruff/format/pyright clean).
**Handoff:** To Reviewer (The Merovingian) for code review.
## Subagent Results

Project config (`workflow.reviewer_subagents`) enables only `preflight` + `security`; the rest are disabled and assessed by the Reviewer directly.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 4 | confirmed 2 (LOW), dismissed 1 (D, factual error), deferred 1 (LOW, out-of-diff) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — Reviewer assessed boundaries directly (empty/None intent_verbs handled by `if cdef.intent_verbs:`) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled — no swallowed errors; the span `with: pass` is a normal CM, no new except blocks |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled — Reviewer assessed test quality directly (no vacuous asserts; AC5 asserts encounter_type; prompt test excises echoed action) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled — Reviewer found 1 stale comment (server-test docstring "Dev phase updates 59-10 assertion" — didn't happen) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled — projection uses typed locals (`list[dict[str, Any]]`); `list(cdef.intent_verbs)` defensively copies |
| 7 | reviewer-security | Yes | findings | 1 | confirmed 1 (MEDIUM, deferred to content-validator follow-up); 3 rules checked, 0 injection/PII/sanitization violations |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled — verify-phase simplify already deduped the otel_capture fixture |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled — Reviewer ran the lang-review checklist directly (see Rule Compliance) |

**All received:** Yes (2 enabled returned; 7 disabled via settings, assessed directly)
**Total findings:** 2 confirmed LOW + 1 confirmed MEDIUM (all non-blocking), 1 dismissed (factual error), 1 deferred (out-of-diff)

## Reviewer Assessment

**Verdict:** APPROVED

The core fix is minimal, correct, and well-tested: `_build_state_summary` routes each confrontation type's authored `intent_verbs` into the router projection (the lexical bridge), omitting the key for verb-less types (backward-compatible), and surfaces `verb_count` on the vocabulary span. 10 new tests, full server suite 9784 passed / 0 failed, ruff clean. No Critical/High findings.

**Observations (adversarially verified, both directions):**
- `[VERIFIED]` **verb_count IS visible to the GM panel** — `sidequest/server/watcher.py:84-96` always emits the flat firehose `agent_span_close` event with `**attrs` (all span attributes), which "Timeline / Timing tabs depend on." The Dev's "GM-panel evidence" comment holds. This **overturns** preflight finding #2 ("the GM panel will not surface verb_count") — that claim was wrong; the typed `SpanRoute.extract` is only a *secondary* projection.
- `[LOW][SIMPLE]` **verb_count omitted from the typed `SpanRoute.extract` lambda** (`sidequest/telemetry/spans/intent_router.py` confrontation-vocabulary route) — inconsistent with its sibling `type_count` which IS in the typed extract. Not a blindness (firehose carries it); a consistency nit. Recommend adding it; non-blocking.
- `[LOW][DOC]` **stale comment** — `test_intent_router_verbal_social_dispatch.py:29-33` docstring says "the Dev phase updates that 59-10 assertion"; Dev correctly did NOT (verb-less fixture → backward-compatible). Recommend trimming the claim.
- `[LOW] genre= kwarg typo` — `_wry_snapshot()` (line 97) calls `GameSnapshot(genre="wry_whimsy")`; `genre` is not a field (correct: `genre_slug`, set on the next line). pyright flags it — BUT the pre-existing `test_intent_router_confrontation_vocabulary.py` has the identical pattern on 6 lines and shipped; pyright is `include=["tests"]` yet NOT in the automated gate (`server-check` = ruff + pytest). Tolerated pre-existing pattern, copied. Recommend `genre_slug=` + drop the redundant line; non-blocking.
- `[MEDIUM][SEC]` **no length bound on `ConfrontationDef.intent_verbs`** — a homebrew pack could author huge verb lists, inflating the router prompt every turn (cost amplification). Confirmed but NON-BLOCKING: the field is *pre-existing* (this diff projects it, doesn't introduce it), authoring is PR-gated, and ADR-134's per-session cost-runaway detector backstops the runaway case. Deferred to a content-schema validator follow-up (fail-loud at pack load per No Silent Fallbacks).
- `[DISMISSED]` preflight #4 ("tests skipped in CI / 361 skipped") — factually wrong: the new tests RUN (verified `10 passed` with `-rs`); the 361 skips are unrelated. The `skipif(!wry_whimsy)` is a deliberate content-availability guard; content is present at the resolved sibling path.

**Data flow traced:** player action → `execute_intent_router_pre_narrator_pass` → `_build_state_summary` projects `confrontation_types` (now with pack-authored `intent_verbs`) → `json.dumps` into `<game_state>` block of the router user prompt → Haiku. Verbs are pack-authored (not player input), same trust boundary as the already-projected `{type, category}`; `json.dumps` escapes correctly (security-confirmed, 0 injection violations).

**Wiring:** `verb_count` → flat firehose → GM panel Timeline/Timing (verified). Decompose span (AC1 OTEL) routed + tested. Confrontation dispatch → bank → `snapshot.encounter` instantiation (AC5, verified in spec-check + asserted in the tightened guard).

### Rule Compliance (lang-review/python.md — assessed directly, rule-checker disabled)

| # | Rule | Result |
|---|------|--------|
| 1 | Silent exception swallowing | PASS — no new except; span `with: pass` is a normal CM |
| 2 | Mutable default arguments | PASS — none added |
| 3 | Type annotations at boundaries | PASS — `_build_state_summary` is private; new locals typed (`projection: list[dict[str, Any]]`) |
| 4 | Logging coverage/correctness | PASS — no new error paths; OTEL span is the observability channel |
| 5 | Path handling | PASS — test path uses `pathlib.Path`; no string concat |
| 6 | Test quality | PASS — no vacuous asserts; AC5 asserts `encounter_type=="persuasion"`; prompt test excises echoed action; skipif carries reason; parametrized cases cover distinct defs |
| 7 | Resource leaks | PASS — span via context manager |
| 8 | Unsafe deserialization | PASS — none |
| 9 | Async pitfalls | PASS — `@pytest.mark.asyncio` correct; fake LLMs are async; no blocking calls |
| 10 | Import hygiene | PASS — verify-phase removed unused OTEL imports; no star imports |
| 11 | Input validation | N/A — pack-authored content, not a user-input boundary (sanitized path unchanged) |
| 12 | Dependency hygiene | N/A — no dependency changes |
| 13 | Fix-introduced regressions | PASS — full suite green; backward-compatible key omission |

### Devil's Advocate

Argue this is broken. **Token amplification:** a malicious or careless homebrew pack authors a `persuasion` type with 500 multi-sentence "verbs"; every router turn for that pack serializes them into the user prompt, inflating cost and possibly crowding the model's attention away from the actual action — the security finding names this, and there's no engine-side cap. *Rebuttal:* pre-existing field, PR-gated authoring, ADR-134 cost ceiling; deferred to a validator follow-up, not introduced here. **Prompt injection via verbs:** a pack author embeds `"], "injected": "ignore prior instructions` as a verb. *Rebuttal:* `json.dumps` escapes quotes/brackets; the verb lands as a JSON string value inside `<game_state>`, identical escaping to the already-projected type/category — no new injection class (security-confirmed). **Empty/None verbs:** a type with `intent_verbs: []` or `None`. *Rebuttal:* `if cdef.intent_verbs:` is falsy for both → key omitted, no empty-list noise. **The fix doesn't actually make Haiku route persuasion:** the verbs reach the prompt but the LLM still might not classify "convince me…" as persuasion. *Rebuttal:* true — that's the irreducible LLM-judgment residual TEA/Architect both logged; the deterministic layers (verbs reach prompt; dispatched confrontation engages) are proven, and live classification is a playtest/59-15 e2e check. **verb_count misleads the GM:** the comment claims panel evidence but the typed route omits it. *Rebuttal:* the flat firehose carries it (verified), so the panel sees it; the typed-route omission is cosmetic. Nothing here rises to blocking.

**Forward notes carried to SM/playtest (from Architect spec-check):** AC3 — confirm a *soft* menace actually auto-enters wonder_shock (vs. degrading to a low-confidence hint) in playtest/59-15; AC4 — the neutral-tag no-emission edge needs turn-10 save verification before any watcher broadening (the type-agnostic dispatch_engagement_watcher is the post-fix home).

**Handoff:** To SM (Morpheus) for finish-story.