---
parent: context-epic-61.md
workflow: tdd
---

# Story 61-14: Reconcile required scene-mechanic rule tokens dropped by 61-12 output compaction

## Business Context

Story 61-12 (done) compacted `narrator_prompts/output_only.md`, and AC#5 replaced the §4
TRIGGER CRITERIA enumeration (the 9-bullet list of confrontation types) with a pointer to
the `begin_confrontation` tool enum. That removal left 8 failing guardrail tests
(`test_required_rule_token_still_present[...]`). Either the guardrail is now stale (the
vocabulary legitimately moved and the narrator no longer needs it) or compaction
over-removed load-bearing prose (the narrator still needs those type names and silently
lost them). Both outcomes matter to the playgroup: a stale-but-passing guardrail gives
false confidence, while genuine over-removal degrades the mechanical scaffold the
mechanics-first players (Sebastien, Jade) rely on. The story's job is to **resolve the
conflict with evidence**, not to make the red bar green by the easiest route.

## Technical Guardrails

- **Failing tests (verified RED 2026-05-27, `8 failed, 13 passed`):**
  `tests/agents/test_61_12_output_format_compaction.py::test_required_rule_token_still_present`
  parametrized over `[ship_combat | dogfight | social_duel | trial | auction | scandal |
  negotiation | chase]`. The `REQUIRED_TOKENS` constant in that file is the assertion target.
- **Prompt source:** `narrator_prompts/output_only.md` (compacted by 61-12) → assembled into
  `NARRATOR_OUTPUT_ONLY`.
- **Migration candidate:** the Intent Router (`sidequest/agents/intent_router.py`) consumes
  `game_state.confrontation_types`, populated at runtime from the genre pack's
  `rules.confrontations` in `sidequest/server/intent_router_pass.py`. ADR-113 / story 59-4
  retired the narrator-signaled `begin_confrontation` tool — the Intent Router now decides
  confrontation type pre-narrator.
- **MEASURE BEFORE DECIDING (load-bearing):** Do not change the test or the prose on
  code-reading alone. Render and inspect BOTH live artifacts: (1) the actually-assembled
  narrator prompt for a real turn, to confirm the tokens are truly gone and no narrator path
  needs them; (2) the live `game_state.confrontation_types` to confirm all 8 names survive
  at runtime. See [[feedback_measure_dont_assert]].
- **No source-text wiring tests** (server CLAUDE.md): if a regression test is needed to pin
  the vocabulary's new home, drive behavior / assert on the rendered enum — never grep the
  prompt source as the assertion.

## Scope Boundaries

**In scope:**
- Resolve the 8 failing `test_required_rule_token_still_present` cases by determining, via
  measurement, which hypothesis holds.
- If migration is confirmed: retarget the guardrail to assert the Intent Router enum carries
  the 8 type names (preserve coverage; do not merely delete the assertion).
- If over-removal is confirmed: restore the necessary tokens to the narrator prose.
- Log a Design Deviation at the decision point recording which hypothesis the measurement
  supported and why.

**Out of scope:**
- Re-litigating 61-12's broader compaction (only the dropped scene-mechanic tokens are in play).
- Any change to ADR-113 / Intent Router confrontation engagement behavior.
- The other compacted rules from 61-12 — only these 8 tokens fail; no evidence other rules
  regressed (confirm in passing, don't expand scope).

## AC Context

- **The 8 tests pass for the RIGHT reason.** Green achieved by measured resolution — either a
  retargeted guardrail (migration confirmed) or restored prose (over-removal confirmed) — NOT
  by deleting the assertion on a code-reading hunch.
- **Coverage is preserved.** If the vocabulary moved, a test still pins that all 8 type names
  are reachable where the system now reads them (the Intent Router enum), so a future
  regression is still caught.
- **Decision is evidenced.** The session/PR records the live-prompt + live-enum measurement
  that drove the choice, and a Design Deviation captures it.

## Assumptions

- **Leading hypothesis (unconfirmed):** the tokens migrated to `game_state.confrontation_types`
  and the narrator no longer needs them post-ADR-113. This is the setup subagent's code-reading
  hypothesis — TEA/Dev must confirm by measurement before acting on it. If measurement
  contradicts it, log a deviation and follow the evidence.
- The genre pack(s) under test actually define all 8 confrontation types in
  `rules.confrontations` (so the enum CAN carry them at runtime).
- 61-12 is fully merged; the prose state under test is the compacted version, not a stale copy.
