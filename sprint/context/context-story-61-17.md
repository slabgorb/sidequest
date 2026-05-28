---
parent: context-epic-61.md
workflow: trivial
---

# Story 61-17: Fix stale test_zones_carry_cache_boundary_flag — narrator_constraints now rides the System/cached bucket

## Business Context

Epic 61 added per-block cache-attribution OTEL (carried over from epic 60) so the
GM panel can prove which prompt sections ride the cached `system_blocks[0]` versus
the uncached per-turn user message — the lie-detector for the 2026-05-23 cost
runaway. `test_zones_carry_cache_boundary_flag` is the regression test guarding that
attribution.

The test currently **fails**, but not because of a cost regression — because the
test's expectation went stale. Story **61-10** (`feat(61-10): promote byte-static
narrator prose to System bucket`, #434, merged) deliberately moved six byte-static
prose sections — including `narrator_constraints` — into `STABLE_SECTION_NAMES`, so
they route to the **System bucket** and ride the cached prefix. That is the intended
cost optimization: byte-static prose loaded from `.md` files with no runtime
interpolation *should* be cached. The test still asserts the pre-61-10 belief that
`narrator_constraints` is a dynamic User-bucket guardrail riding the uncached message.

This story reconciles the test with the shipped reality. It is a **test-only fix** —
the production code (61-10) is correct and must not be reverted.

## Technical Guardrails

**Key files:**

| Path | Role |
|------|------|
| `sidequest-server/tests/agents/test_prompt_cache_attribution_otel.py:203` | The stale assertion (`narrator_constraints` `cached is False`) — fix here |
| `sidequest-server/sidequest/agents/prompt_framework/bucket.py:71` | `narrator_constraints` in `STABLE_SECTION_NAMES` → `SectionBucket.System` (source of truth; do NOT change) |
| `sidequest-server/sidequest/agents/prompt_framework/bucket.py:~83` | `default_bucket_for_section` — System if in STABLE, else User |

**Current failure (verified, serial run):**

```
AssertionError: narrator_constraints is a User-bucket guardrail — it lands in the
per-turn user message, NOT the cached system_blocks[0], even though it sits in Primacy
assert True is False                 # actual cached=True, asserted False
```

**Patterns / constraints:**

- This is a **legitimate test-expectation correction**, not a source-text wiring
  test — the assertion reads the framework's computed `cached` flag, not grepped
  source. (Distinct from the CLAUDE.md "No Source-Text Wiring Tests" prohibition.)
- The sibling assertion at line ~197 (`narrator_identity` `cached is True`) is
  correct and stays. Only the `narrator_constraints` assertion (and its explanatory
  comment claiming "User-bucket guardrail") is stale.
- Update the **comment** as well as the assertion: the rationale text on lines
  ~195-205 articulates the old "guardrails ride the uncached message" model. Post-61-10,
  `narrator_constraints` is byte-static prose, not a per-turn guardrail. The comment
  should reflect that a System-bucket byte-static section in Primacy *does* ride the
  cached block.

**What NOT to touch:** `bucket.py` / `STABLE_SECTION_NAMES` (that is the 61-10
decision); the `narrator_identity` assertion; the AC-2 usage-join tests below it.

## Scope Boundaries

**In scope:**
- Flip `narrator_constraints` cached expectation `False → True` at
  `test_prompt_cache_attribution_otel.py:203`.
- Rewrite the accompanying comment to describe the post-61-10 reality (byte-static
  System-bucket prose rides the cached prefix).
- Confirm the full file goes green (the other 8 tests already pass).

**Out of scope:**
- Any change to `bucket.py` or production prompt assembly.
- Re-litigating whether `narrator_constraints` *should* be cached — 61-10 settled
  that; see the 61-15 note below.
- The other guardrails' zone/bucket placement (61-18 covers the SDK-path guardrail
  audit).

## AC Context

**AC-1 — `test_zones_carry_cache_boundary_flag` passes.** After the assertion +
comment fix, run:
```
uv run pytest tests/agents/test_prompt_cache_attribution_otel.py -n0
```
Expect 9 passed (was 1 failed, 8 passed). The flipped assertion now matches the
framework's computed `cached=True` for `narrator_constraints`.

**AC-2 — no production change.** `git diff` touches only the test file. `bucket.py`
and orchestrator prompt assembly are untouched.

**Edge case:** confirm the section's *zone* (Primacy vs Stable) as well as its
bucket — the cached verdict is `bucket == System AND zone ∈ {Primacy, Early}`. If the
framework places `narrator_constraints` outside Primacy/Early, the computed value
could differ; align the assertion to whatever the framework actually computes, and let
the comment explain it. Do not hard-code an expectation that fights the framework.

## Assumptions

- **61-15 is superseded by this story.** 61-15 framed the *same* failing test with the
  opposite fix ("force `narrator_constraints` to `cached=False`"), which would revert
  61-10's optimization. 61-15's premise predates 61-10's recognition that
  `narrator_constraints` is byte-static prose (not a dynamic guardrail). Recommend
  closing 61-15 as superseded before/at this story's finish. If 61-15 is still open
  when this lands, flag it as a Design Deviation.
- The production caching behavior (61-10) is correct and stays. If profiling later
  shows a byte-static guardrail genuinely needs per-turn freshness, that is a *new*
  design decision (ADR-111 territory), not this test fix.
