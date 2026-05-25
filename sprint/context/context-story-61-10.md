# Story Context: 61-10 — Promote byte-static narrator prose to System bucket

## Summary

Six narrator prose sections are byte-identical across every turn of a game session but currently land in the User bucket, meaning they're re-sent (and re-billed as cache-write) on every narrator call. They meet the STABLE_SECTION_NAMES criterion and should be promoted to SectionBucket.System so they ride the cached system prefix.

## Technical Approach

The change is surgical:

1. **Add six names to `STABLE_SECTION_NAMES`** in `sidequest/agents/prompt_framework/bucket.py` (line ~28). This is a `frozenset` that controls which sections get `SectionBucket.System` routing via `default_bucket_for_section()`.

2. **The six sections to promote:**
   - `narrator_constraints` — constraints.md (~112 tok)
   - `narrator_agency` — agency.md (~201 tok)
   - `narrator_consequences` — consequences.md (~71 tok)
   - `narrator_pov_rules` — pov_rules.md (~200 tok)
   - `narrator_referral_rule` — referral_rule.md (~65 tok)
   - `narrator_output_style` — output_style.md (~115 tok)

3. **Regression test** in `tests/agents/test_prompt_framework/test_bucket.py` asserting each name maps to System.

## Why These Six Qualify

Per bucket.py's own docstring, STABLE_SECTION_NAMES is for sections that are "byte-identical across every turn of the same game." All six are loaded from static `.md` files by `narrator_prompts/__init__.py` with no runtime interpolation — they are literally the same bytes every turn. They were omitted at the ADR-098/111 cutover, not deliberately excluded.

## Verification

- AC-1/2/3 are testable in CI (frozenset membership + bucket routing + regression test)
- AC-4/5 require a live playtest to confirm OTEL spans and token-count delta — these are post-merge validation, not blocking for the code change itself

## Risk

Minimal. The only side effect is a one-time cache-prefix invalidation on first deploy (the system prefix changes shape, so the first call pays full cache-write). After that, every subsequent call saves ~764 tok of cache-write.

## Dependencies

- ADR-098: Stateless Narrator Turns
- ADR-111: Recency-Zone Narrator Guardrails (deferred, but bucket.py is live)
- ADR-112: Genre Prose Cache Promotion (partial — this story extends it)
