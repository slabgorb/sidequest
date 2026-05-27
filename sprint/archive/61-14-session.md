---
story_id: "61-14"
jira_key: ""
epic: "61"
workflow: "tdd"
---
# Story 61-14: Reconcile required scene-mechanic rule tokens dropped by 61-12 output compaction

## Story Details
- **ID:** 61-14
- **Epic:** 61
- **Workflow:** tdd
- **Points:** 3 (P1)
- **Type:** bug
- **Stack Parent:** none

## Story Context

Story 61-12 compacted the narrator_prompts/output_only.md file by ~50%, including replacing the §4 TRIGGER CRITERIA enumeration (9-bullet list of confrontation types: ship_combat, dogfight, social_duel, trial, auction, scandal, negotiation, chase) with a pointer to the begin_confrontation tool enum. This removal has caused 8 test failures in `test_61_12_output_format_compaction.py::test_required_rule_token_still_present[{type}]`.

The story description notes a CONFLICT requiring measurement before deciding: either (a) the tokens legitimately moved to a tool enum and the test is stale (needs retargeting), or (b) the compaction over-removed and the prose must still name them.

## Workflow Tracking
**Workflow:** tdd
**Phase:** spec-check
**Phase Started:** 2026-05-27T15:05:03Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-27T18:00:00Z | 2026-05-27T14:52:34Z | -11246s |
| red | 2026-05-27T14:52:34Z | 2026-05-27T14:59:51Z | 7m 17s |
| green | 2026-05-27T14:59:51Z | 2026-05-27T15:05:03Z | 5m 12s |
| spec-check | 2026-05-27T15:05:03Z | - | - |

## Sm Assessment

**Setup complete — routing to TEA (Fezzik) for RED phase.**

61-14 is a **verified-real** P1 bug (SM ran the 8 named tests: `8 failed, 13 passed`,
2026-05-27) — unlike the two stale stories ahead of it this session (59-12 parked, 59-18
closed-by-landed-work). The work is to **resolve a measure-first conflict**, not to turn
the bar green by the cheapest route.

- **Repos:** server only. Branch `feat/61-14-scene-mechanic-rule-tokens-dropped-by-61-12`
  off develop (github-flow subrepo).
- **Workflow:** tdd → next agent **tea**, next phase **red**.
- **Context:** `sprint/context/context-story-61-14.md` (validates OK).
- **CRITICAL — the fork is OPEN.** sm-setup's "Conclusion: Hypothesis A, test is stale" was
  code-reading, and I demoted it to a hypothesis and cleared its premature Design Deviation.
  The story mandates measuring the LIVE narrator prompt AND the LIVE Intent Router enum
  before touching the guardrail. Do not delete coverage on a hunch — retarget if migration
  is confirmed, restore prose if over-removal is confirmed. See [[feedback_measure_dont_assert]].

## TEA Assessment

**Phase:** spec-check → resolved in the test layer (no Dev green-phase work)
**Tests Required:** N/A — this was a guardrail **reconciliation**, not a new feature.
**Status:** GREEN. Target file `test_61_12_output_format_compaction.py`: **31 passed**
(was 8 failed / 13 passed). 59-10 coverage `test_intent_router_confrontation_vocabulary.py`:
**6 passed**. `REQUIRED_TOKENS` is local to the one test file (no other importers).

**The fork is resolved — Hypothesis A, by measurement (not code-reading):** the 8
confrontation-type tokens legitimately left the narrator surface. Evidence in the Design
Deviation above (deleted test_50_2; retired begin_confrontation; zero of 8 tokens in the
live SDK narrator prompt; legacy guardrail SDK-gated-off; vocabulary now pack-sourced into
the Intent Router via 59-10 with OTEL + existing coverage).

**Resolution applied (test-only):** removed the 8 stale tokens from `REQUIRED_TOKENS`,
replaced with a banner comment recording the migration + measurement (silent-omission ban
satisfied). No production source touched. No new test needed — 59-10 already guards the new
home; the genre type names are content (not engine constants) and are correctly tested
against a synthetic fixture pack.

**Handoff:** There is **no Dev implementation** for this story — the "bug" was a stale
guardrail left behind when test_50_2 was deleted and 59-10 migrated the vocabulary. Recommend
SM route straight to Reviewer/finish (light path), not a green phase. Single-repo (server),
single test file, ~20 lines changed.

### Rule Coverage

| Rule (server CLAUDE.md) | How honored |
|------|------|
| No source-text wiring tests | Used live `build_narrator_prompt` measurement + 59-10's behavior test, not a prose grep |
| Tests must not point at live content | Removed hardcoded genre type names; the new-home test uses a synthetic fixture pack |
| Measure, don't assert | Built the real SDK prompt + ran the projection before concluding; demoted setup's code-read hypothesis |
| No silent omission | Removed tokens are documented in an in-file banner + this deviation |

## Dev Assessment

**Implementation Complete:** Yes — **no production code required.** Confirmed the resolution
was correctly test-only (TEA's measured Hypothesis-A reconciliation). I did not write or
change any production code; the minimalist-discipline answer to "is this necessary?" is no.

**Files Changed:** none by Dev. TEA's commit `aa1d217` (test-only) is the entire change.

**Tests (GREEN, verified via testing-runner, serial -n0):**
- `tests/agents/test_61_12_output_format_compaction.py` — **31/31 pass** (was 8 failed)
- `tests/server/test_intent_router_confrontation_vocabulary.py` — **6/6 pass** (migrated-home coverage)
- `tests/agents/` (full dir) — 1099 passed, 399 skipped, **1 failed** — the one failure
  (`test_prompt_cache_attribution_otel.py::test_zones_carry_cache_boundary_flag`) is UNRELATED
  and pre-existing (see Delivery Findings). My/TEA's diff removed only string literals from a
  local tuple in `test_61_12`; it cannot affect cache-bucket attribution in a different file.

**Branch:** `feat/61-14-scene-mechanic-rule-tokens-dropped-by-61-12` — pushed to origin.

**Handoff:** To next phase (verify/review). This was a stale-guardrail reconciliation, not a
feature — review should be light (single test file, ~20 lines, no production change).

## Delivery Findings

### Dev (implementation)
- **Gap** (non-blocking): `tests/agents/test_prompt_cache_attribution_otel.py::test_zones_carry_cache_boundary_flag`
  fails on this branch and is **pre-existing / unrelated to 61-14**. It asserts
  `narrator_constraints` is a User-bucket (uncached) guardrail, but story 61-10 (commit
  `5201b57`, "promote byte-static narrator prose to System bucket #434") promoted it to the
  System/cached bucket without updating this test's expectation. Affects
  `tests/agents/test_prompt_cache_attribution_otel.py` (retarget the assertion to expect
  `cached=True` for `narrator_constraints`, or confirm 61-10's promotion was intended).
  Needs its own story — do NOT fix under 61-14 (scope). *Found by Dev during implementation.*

### TEA (test design)
- **Improvement** (non-blocking): `CONFRONTATION_TRIGGER_CONSTRAINT` (narrator_guardrails.py)
  still enumerates the 8 confrontation types but only reaches the narrator on the retired
  legacy backend (`_maybe_register_legacy_guardrail` SDK-gate). On the SDK path (ADR-111) it
  is dead prose. Worth an audit: either confirm the SDK narrator needs no confrontation-trigger
  guardrail (Intent Router owns it) or migrate the rule to the tool/cached-prose surface ADR-111
  specifies. Affects `sidequest/agents/narrator_guardrails.py` + `orchestrator.py:2378-2383`.
  Out of scope for 61-14 (it's about REQUIRED_TOKENS); flagging for a future story.
  *Found by TEA during test design.*

## Delivery Findings (setup — superseded by measurement above)

### Measurement: Live Prompt Inspection

The confrontation type tokens (ship_combat, dogfight, social_duel, trial, auction, scandal, negotiation, chase) were removed from NARRATOR_OUTPUT_ONLY per story 61-12 AC#5. The conflict branch is between two hypotheses:

**Hypothesis A: Tokens moved to Intent Router / game_state.confrontation_types**
- The Intent Router system prompt (sidequest/agents/intent_router.py) references types via `game_state.confrontation_types[].type`, which is populated from the genre pack's rules.confrontations at runtime (sidequest/server/intent_router_pass.py).
- The narrator never chooses confrontation type anymore (ADR-113 Story 59-4 retired begin_confrontation). The Intent Router makes that decision before the narrator runs.
- The narrator only narrates already-active encounters; the type is encoded in the encounter state, not chosen by the narrator.
- REQUIRED_TOKENS test assertion targets an outdated mental model: "narrator must know available types". The narrator doesn't decide type; Intent Router does.

**Hypothesis B: Test is correct; tokens must stay in narrator prose**
- Would apply if the narrator path had any decision point requiring knowledge of the type enum.
- Current code inspection shows no such decision point in narrator.py or orchestrator.py's narrator-calling paths.

**Status — HYPOTHESIS ONLY, NOT YET MEASURED (SM correction):** The above is
code-reading, not measurement. The story mandates "measure the live prompt before
deciding," and project rule [[feedback_measure_dont_assert]] forbids announcing a
code-derived hypothesis as a conclusion. Hypothesis A (tokens legitimately migrated
to the Intent Router's `game_state.confrontation_types`; narrator no longer needs
them post-ADR-113/59-4) is the **leading candidate** — but it MUST be confirmed by
TEA/Dev actually rendering BOTH live artifacts before any test is touched:
  1. The live assembled **narrator** prompt (NARRATOR_OUTPUT_ONLY as actually built
     for a real turn) — confirm the 8 tokens are genuinely absent and that no
     narrator decision path still needs them.
  2. The live **Intent Router** input — confirm `game_state.confrontation_types`
     actually carries all 8 type names at runtime from the genre pack.

Do NOT delete the guardrail assertion on the strength of code-reading. The test
`test_required_rule_token_still_present` is a guardrail that exists to catch
over-removal (Hypothesis B); disarming it requires positive evidence the rule it
pins is truly obsolete AND that the vocabulary survives somewhere the system still
reads. If measurement confirms migration, retarget the guardrail to assert the Intent
Router enum carries the tokens (don't just delete the coverage).

### Outstanding Questions

1. **Test retargeting strategy:** Should test_required_rule_token_still_present remove the 8 confrontation-type tokens from REQUIRED_TOKENS? Or should a new test in test_intent_router_confrontation_vocabulary.py assert that all genre-loaded types are available to the router?
   - Recommended: Remove from REQUIRED_TOKENS with a Design Deviation note. The rule the tokens pinned no longer applies. If a regression test is needed, it should test the Intent Router's ability to access game_state.confrontation_types, not the narrator's knowledge of them.

2. **Prose completeness check:** Has story 61-12's compaction preserved all other load-bearing rules from the original narrator prompt? The failing tests suggest at least the 8 type names are missing; no other failures are reported, so other rules likely survived.

## Design Deviations

None at setup time.

<!-- The implementing agent (TEA/Dev) logs a deviation IF and WHEN they change the
guardrail test — and only AFTER measuring both live artifacts. sm-setup pre-authored a
deviation choosing option (a); SM cleared it as premature (it prejudged the
measure-first fork). Do not deviate on code-reading alone. -->

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Removed 8 confrontation-type tokens from REQUIRED_TOKENS (guardrail retarget, not silent omission)**
  - Spec source: tests/agents/test_61_12_output_format_compaction.py::REQUIRED_TOKENS + its docstring
  - Spec text: "If a token genuinely no longer belongs in this file (because the rule moved …), log a Design Deviation and remove it from REQUIRED_TOKENS — silent omission is forbidden."
  - Implementation: removed ship_combat, dogfight, social_duel, trial, auction, scandal, negotiation, chase from REQUIRED_TOKENS; replaced with an in-file banner comment recording the migration + measurement. No production source changed.
  - Rationale: MEASURED (not code-read) — Hypothesis A confirmed. (1) The test these tokens were "load-bearing for", test_50_2_confrontation_trigger_prompt, no longer exists. (2) begin_confrontation tool is retired (agents/tools/_retired/). (3) Live SDK narrator prompt (the only viable backend post-61-9) contains NONE of the 8 tokens — built it via Orchestrator.build_narrator_prompt for space_opera and asserted absence. (4) The legacy injection of CONFRONTATION_TRIGGER_CONSTRAINT (which does name them) is gated to the NON-SDK backend in _maybe_register_legacy_guardrail (ADR-111). (5) The vocabulary's real home is game_state.confrontation_types, sourced from pack.rules.confrontations (intent_router_pass.py:107-115, story 59-10), consumed by the pre-narrator Intent Router (ADR-113), WITH an OTEL span and existing coverage at tests/server/test_intent_router_confrontation_vocabulary.py (6 passed). Hardcoding the 8 genre type names in an engine test is also the content-coupling anti-pattern (feedback_tests_not_point_at_content); they are CONTENT, correctly guarded against a synthetic fixture pack instead.
  - Severity: minor
  - Forward impact: none. No production behavior change. Coverage preserved (59-10 test). test_50_2 already gone. If a future genre adds confrontation types, the dynamic pack→router projection carries them with zero narrator-prompt edits.

### Dev (implementation)
- No deviations from spec. No production code was written — the story's correct resolution
  (TEA's measured Hypothesis-A reconciliation) is test-only, and minimalist-discipline says
  add nothing a test doesn't demand. Dev verified GREEN and pushed the branch; nothing to deviate.